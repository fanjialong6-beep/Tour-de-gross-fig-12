"""独立复核保存的每个代表元，重算轨道及 Z/X 对偶关系。"""
import argparse
import json
from pathlib import Path
import numpy as np
from bicycle.codes import make_code
from bicycle.orbits import ShiftOrbits


def verify(path):
    result=json.loads(Path(path).read_text(encoding='utf-8'))
    c=make_code(result['config']['code']); sector=result['config']['sector']
    check,opposite=(c.hz,c.lz) if sector=='X' else (c.hx,c.lx)
    report={}
    for weight,record in result['weights'].items():
        orbits=ShiftOrbits(c)
        for support,expected_size in zip(record['representatives'],record['orbit_sizes'],strict=True):
            v=np.zeros(c.n,dtype=np.uint8); v[support]=1
            assert len(support)==len(set(support))==int(weight)
            assert not np.any(check@v%2)
            assert np.any(opposite@v%2), '误把稳定子当作非平凡逻辑算符'
            new,i=orbits.add(v); assert new
            assert orbits.sizes[i]==expected_size
            dual=c.zx_dual(v)
            dual_check=c.hx if sector=='X' else c.hz
            assert not np.any(dual_check@dual%2)
        assert len(orbits.sizes)==record['shift_unique']
        assert sum(orbits.sizes)==record['all_shifts']
        assert len(record['curve'])==record['hits']
        if record['saturated']:
            assert record['stale_hits']>=result['config']['patience']*len(orbits.sizes)
        report[weight]={'valid_representatives':len(orbits.sizes),'all_shifts':sum(orbits.sizes)}
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('results',nargs='+'); args=p.parse_args()
    for path in args.results:
        print(path,verify(path))
