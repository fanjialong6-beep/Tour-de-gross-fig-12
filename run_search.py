"""命令行入口；在项目根目录运行。示例见 README.md。"""
import argparse
from bicycle.search import run_search

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='独立生成 Fig.12 的一个码、一个 Pauli 类型的两条曲线')
    p.add_argument('--code', choices=['gross','two_gross'], required=True)
    p.add_argument('--sector', choices=['X','Z'], required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--seed', type=int, default=20260923)
    p.add_argument('--max-trials', type=int, default=2000000)
    p.add_argument('--max-seconds', type=float, default=1800)
    p.add_argument('--patience', type=int, default=10)
    p.add_argument('--bp-method', choices=['minimum_sum','product_sum'], default='minimum_sum')
    p.add_argument('--ms-scaling-factor', type=float, default=1.0)
    p.add_argument('--no-dressing', action='store_true')
    args = p.parse_args()
    if args.max_trials < 1 or args.max_seconds <= 0 or args.patience < 1:
        p.error('预算和 patience 必须为正数')
    run_search(args.code, args.sector, args.out, args.seed, args.max_trials,
               args.max_seconds, args.patience, args.bp_method,
               args.ms_scaling_factor, not args.no_dressing)
