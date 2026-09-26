"""运行四组搜索、验证代表元并绘制 Fig. 12。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from plot_results import plot
from verify_results import verify


def main():
    p=argparse.ArgumentParser(description='Fig.12 一键复现')
    p.add_argument('--workers',type=int,choices=range(1,5),default=2)
    p.add_argument('--max-seconds',type=float,default=1800)
    p.add_argument('--max-trials',type=int,default=2000000)
    p.add_argument('--seed',type=int,default=2026092301)
    p.add_argument('--out',default=None)
    args=p.parse_args()
    if args.max_seconds<=0 or args.max_trials<1:
        p.error('实验预算必须为正')
    root=Path(__file__).resolve().parent
    out=(root/args.out) if args.out else root/'results'/datetime.now().strftime('run_%Y%m%d_%H%M%S')
    out.mkdir(parents=True,exist_ok=False)
    jobs=[(name,sector,args.seed+i) for i,(name,sector) in enumerate(
          [('gross','X'),('gross','Z'),('two_gross','X'),('two_gross','Z')])]

    def execute(job):
        name,sector,seed=job
        directory=out/f'{name}_{sector}'
        command=[sys.executable,'-u',str(root/'run_search.py'),'--code',name,
                 '--sector',sector,'--seed',str(seed),'--out',str(directory),
                 '--max-seconds',str(args.max_seconds),'--max-trials',str(args.max_trials)]
                                            
        with (out/f'{name}_{sector}.log').open('w',encoding='utf-8') as log:
            print(f'Start {name}/{sector}; log: {log.name}',flush=True)
            process=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
        if process.returncode:
            raise RuntimeError(f'{name}/{sector} failed. See log in {out}')
        path=directory/'result.json'
        print(f'Finished {name}/{sector}',flush=True)
        return str(path)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        paths=list(pool.map(execute,jobs))
    checks={Path(path).parent.name:verify(path) for path in paths}
    (out/'verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    plot(paths,out/'figure')
    print(f'Completed. Results: {out}',flush=True)


if __name__=='__main__':
    main()
