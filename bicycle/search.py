"""随机逻辑约束 + BP+OSD。所有曲线都由实际命中记录生成。"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
from ldpc import BpOsdDecoder
from .codes import make_code
from .orbits import ShiftOrbits


def dump_json(path, obj):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def run_search(code_name, sector, outdir, seed, max_trials=2000000,
               max_seconds=1800, patience=10, bp_method='minimum_sum',
               ms_scaling_factor=1.0, dress_logical=True, checkpoint_every=1000):
    """论文停止规则逐重量执行；参考计数不参与搜索或停止判定。

    BP 更新规则/缩放系数未在 Fig.12 图注中指定，作为显式配置记录。
    dress_logical=True 在随机非零逻辑类代表上加随机稳定子（附录 A.8）。
    """
    code = make_code(code_name)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir/'result.json').exists() or (outdir/'events.jsonl').exists():
        raise FileExistsError(f'为保留证据，请换一个结果目录：{outdir}')
    check, logicals = (code.hz, code.lz) if sector == 'X' else (code.hx, code.lx)
    opposite_stabilizers = check
    iterations, order = (20, 0) if code_name == 'gross' else (40, 7)
    rng = np.random.default_rng(seed)
    targets = (code.distance, code.distance+2)
    buckets = {w: {'orbits': ShiftOrbits(code), 'hits': 0, 'last_new': 0,
                   'curve': [], 'done': False, 'stop_trial': None} for w in targets}
    hist = Counter()
    started = time.monotonic()
    trial = 0
    bp_converged = 0
    invalid = 0
    reason = 'max_trials'
    config = dict(code=code_name, sector=sector, seed=seed, max_trials=max_trials,
                  max_seconds=max_seconds, patience=patience, bp_method=bp_method,
                  ms_scaling_factor=ms_scaling_factor, schedule='parallel',
                  max_iter=iterations, osd_order=order,
                  osd_method='OSD_0' if order == 0 else 'OSD_CS',
                  prior_distribution='uniform[0.01,0.99)', dress_logical=dress_logical,
                  random_logical='uniform nonzero coefficient vector in a GF(2) quotient basis',
                  stop_policy='freeze each weight after patience * discovered_orbits hits without a new orbit',
                  python=sys.version, platform=platform.platform(),
                  packages={p: importlib.metadata.version(p) for p in ('numpy','scipy','ldpc')},
                  command=sys.argv, started_utc=datetime.now(timezone.utc).isoformat(),
                  code_invariants=code.validate())
    config['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in Path(__file__).parent.glob('*.py')}
    dump_json(outdir/'config.json', config)
    np.savez_compressed(outdir/'code_matrices.npz', hx=code.hx, hz=code.hz, lx=code.lx, lz=code.lz)

    def snapshot(status):
        payload = {'config': config, 'trials': trial, 'elapsed_seconds': time.monotonic()-started,
                   'status': status, 'bp_converged': bp_converged, 'invalid_syndromes': invalid,
                   'decoded_weight_histogram': dict(sorted(hist.items())), 'weights': {}}
        for w, b in buckets.items():
            orbit = b['orbits']
            payload['weights'][str(w)] = {
                'hits': b['hits'], 'shift_unique': len(orbit.sizes),
                'all_shifts': sum(orbit.sizes), 'orbit_sizes': orbit.sizes,
                'last_new_hit': b['last_new'], 'stale_hits': b['hits']-b['last_new'],
                'saturated': b['done'], 'stop_trial': b['stop_trial'], 'curve': b['curve'],
                'representatives': [np.flatnonzero(v).tolist() for v in orbit.representatives]}
        dump_json(outdir/'result.json', payload)
        return payload

                                           
    with (outdir/'events.jsonl').open('w', encoding='utf-8', buffering=1) as events:
        try:
            for trial in range(1, max_trials+1):
                if time.monotonic()-started >= max_seconds:
                    trial -= 1
                    reason = 'time_limit'
                    break
                coeff = rng.integers(0, 2, size=12, dtype=np.uint8)
                while not coeff.any():
                    coeff = rng.integers(0, 2, size=12, dtype=np.uint8)
                constraint = (coeff @ logicals) % 2
                if dress_logical:
                    dress = rng.integers(0, 2, size=len(opposite_stabilizers), dtype=np.uint8)
                    constraint ^= (dress @ opposite_stabilizers) % 2
                                                      
                pcm = np.vstack([check, constraint])
                syndrome = np.zeros(len(pcm), dtype=np.uint8)
                syndrome[-1] = 1
                priors = rng.uniform(0.01, 0.99, code.n)
                decoder = BpOsdDecoder(pcm, error_channel=priors.tolist(), max_iter=iterations,
                                      bp_method=bp_method, ms_scaling_factor=ms_scaling_factor,
                                      schedule='parallel', osd_method=config['osd_method'],
                                      osd_order=order)
                vector = np.asarray(decoder.decode(syndrome), dtype=np.uint8).copy()
                valid = np.array_equal((pcm @ vector) % 2, syndrome)
                bp_converged += bool(decoder.converge)
                if not valid:
                    invalid += 1
                    raise RuntimeError(f'解码输出不满足方程，trial={trial}')
                weight = int(vector.sum())
                hist[weight] += 1
                row = {'trial': trial, 'weight': weight, 'bp_converged': bool(decoder.converge)}
                if weight in buckets and not buckets[weight]['done']:
                    b = buckets[weight]
                    b['hits'] += 1
                    new, orbit_id = b['orbits'].add(vector)
                    if new:
                        b['last_new'] = b['hits']
                    count = len(b['orbits'].sizes)
                    b['curve'].append([b['hits'], count])
                    row.update(hit=b['hits'], new=new, orbit_id=orbit_id)
                    if b['hits']-b['last_new'] >= patience*count:
                        b['done'] = True
                        b['stop_trial'] = trial
                events.write(json.dumps(row)+'\n')
                if trial % checkpoint_every == 0:
                    snapshot('running')
                    print(f'{code_name}/{sector} trial={trial} ' + ' '.join(
                        f'w{w}: {len(b["orbits"].sizes)} orbits/{b["hits"]} hits' for w,b in buckets.items()), flush=True)
                if all(b['done'] for b in buckets.values()):
                    reason = 'paper_stopping_rule'
                    break
        except KeyboardInterrupt:
            reason = 'interrupted'
        except Exception:
            snapshot('failed')
            raise
    result = snapshot(reason)
    print(f'{code_name}/{sector}: {reason}, {trial} trials, {result["elapsed_seconds"]:.1f}s', flush=True)
    return result
