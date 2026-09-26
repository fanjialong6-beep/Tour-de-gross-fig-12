"""根据 result.json 绘制八条发现曲线并输出对照表。"""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(inputs, outdir):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    targets = json.loads((Path(__file__).parent/'paper_targets.json').read_text(encoding='utf-8'))
    data = [json.loads(Path(p).read_text(encoding='utf-8')) for p in inputs]
    data.sort(key=lambda r: (r['config']['code']!='gross', r['config']['sector']))
    fig, ax = plt.subplots(figsize=(8.5, 6.3), constrained_layout=True)
    colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f']
    rows = []
    for result in data:
        cfg=result['config']; name=cfg['code']; sector=cfg['sector']; n=cfg['code_invariants']['n']
        base=(0 if name=='gross' else 4)+(0 if sector=='X' else 2)
        for j,(weight, w) in enumerate(result['weights'].items()):
            curve=w['curve']
            if curve:
                xs,ys=zip(*curve)
                ax.step(xs,ys,where='post',color=colors[base+j],lw=1.7,
                        linestyle='-' if name=='gross' else '--',label=f'{n}q: {sector}, weight {weight}')
            target=targets[name][weight]
            rows.append(dict(code=name,sector=sector,weight=weight,hits=w['hits'],
                             shift_unique=w['shift_unique'],paper_shift_unique=target['shift_unique'],
                             all_shifts=w['all_shifts'],paper_all_shifts=target['all_shifts'],
                             counts_match=w['shift_unique']==target['shift_unique'] and w['all_shifts']==target['all_shifts'],
                             stopping_rule_met=w['saturated'],trials=result['trials'],
                             elapsed_seconds=round(result['elapsed_seconds'],2),seed=cfg['seed']))
    for index, level in enumerate((3, 12, 30, 274)):
        ax.axhline(level, color='0.35', lw=1.6, ls='--', alpha=0.95, zorder=1,
                   label='Paper reference counts' if index == 0 else None)
        ax.text(0.985, level, f'paper {level}', transform=ax.get_yaxis_transform(),
                ha='right', va='bottom', fontsize=8.5, color='0.25', fontweight='semibold',
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.72, pad=0.6))
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_yticks([1,3,12,30,100,274],labels=['1','3','12','30','100','274'])
    ax.set_xlabel('Count of sampled operators with the specified weight')
    ax.set_ylabel('Count of shift-unique operators')
    ax.set_title('Enumerating low-weight logical operators\nIndependent reproduction of Fig. 12',fontsize=14)
    if ax.get_legend_handles_labels()[0]: ax.legend(loc='upper left',fontsize=9)
    ax.text(0.01,-.17,'Curves: actual BP+OSD search. Dark gray dashed lines: paper reference counts.',
            transform=ax.transAxes,fontsize=9,color='#555555')
    fig.savefig(outdir/'fig12_reproduced.png',dpi=200)
    fig.savefig(outdir/'fig12_reproduced.svg')
    plt.close(fig)
    with (outdir/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (outdir/'comparison.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    for row in rows: print(row)
    return rows


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('results',nargs='+'); p.add_argument('--out',default='results/figure')
    args=p.parse_args(); plot(args.results,args.out)
