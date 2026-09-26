"""使用 XOR 实现二元域 F_2 线性代数。"""
import numpy as np


def rref(matrix):
    """返回输入矩阵的行最简形和主元列。"""
    a = np.asarray(matrix, dtype=np.uint8).copy() % 2
    pivots = []
    for col in range(a.shape[1]):
        candidates = np.flatnonzero(a[len(pivots):, col])
        if len(candidates) == 0:
            continue
        row = len(pivots)
        other = row + candidates[0]
        a[[row, other]] = a[[other, row]]
        eliminate = np.flatnonzero(a[:, col])
        eliminate = eliminate[eliminate != row]
        a[eliminate] ^= a[row]
        pivots.append(col)
        if len(pivots) == a.shape[0]:
            break
    return a, pivots


def rank(matrix):
    return len(rref(matrix)[1])


def nullspace(matrix):
    """返回满足 matrix @ basis.T = 0 (mod 2) 的零空间基。"""
    a, pivots = rref(matrix)
    free = [j for j in range(a.shape[1]) if j not in pivots]
    basis = np.zeros((len(free), a.shape[1]), dtype=np.uint8)
    for i, col in enumerate(free):
        basis[i, col] = 1
        basis[i, pivots] = a[:len(pivots), col]
    return basis


def quotient_basis(kernel_check, stabilizers):
    """返回 ker(kernel_check) / row(stabilizers) 的逻辑算符代表元基。"""
    pivots = {}

    def insert(row):
        value = int.from_bytes(np.packbits(row, bitorder='little').tobytes(), 'little')
        while value:
            p = value.bit_length() - 1
            if p not in pivots:
                pivots[p] = value
                return True
            value ^= pivots[p]
        return False

    for row in stabilizers:
        insert(row)
    result = [row for row in nullspace(kernel_check) if insert(row)]
    return np.asarray(result, dtype=np.uint8).reshape(-1, kernel_check.shape[1])
