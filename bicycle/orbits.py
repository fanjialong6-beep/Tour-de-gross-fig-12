"""按全体物理平移去重。此处不能把相差稳定子的算符全部合并。"""
import numpy as np


def key(vector):
    return np.packbits(vector, bitorder='little').tobytes()


class ShiftOrbits:
    def __init__(self, code):
        self.code = code
        self.lookup = {}
        self.representatives = []
        self.sizes = []
                                                         
        self.permutations = np.asarray([
            [code.index(block, x+dx, y+dy)
             for block in range(2) for x in range(code.ell) for y in range(code.m)]
            for dx in range(code.ell) for dy in range(code.m)], dtype=np.int32)

    def add(self, vector):
        packed = key(vector)
        if packed in self.lookup:
            return False, self.lookup[packed]
        support = np.flatnonzero(vector)
        shifts = np.zeros((self.code.ell*self.code.m, self.code.n), dtype=np.uint8)
        shifts[np.arange(len(shifts))[:, None], self.permutations[:, support]] = 1
        orbit = set(map(bytes, np.packbits(shifts, axis=1, bitorder='little')))
        representative_key = min(orbit)
        representative = np.unpackbits(np.frombuffer(representative_key, dtype=np.uint8),
                                       bitorder='little')[:self.code.n].copy()
        index = len(self.sizes)
        self.lookup.update(dict.fromkeys(orbit, index))
        self.representatives.append(representative)
        self.sizes.append(len(orbit))
        return True, index
