from dataclasses import dataclass
import numpy as np
from .gf2 import quotient_basis, rank


@dataclass
class BBCode:
    name: str
    ell: int
    m: int
    distance: int  
    hx: np.ndarray
    hz: np.ndarray
    lx: np.ndarray
    lz: np.ndarray

    @property
    def n(self):
        return 2 * self.ell * self.m

    def index(self, block, x, y):
        """将 L/R 块和环面坐标映射到向量索引。"""
        return block * self.ell * self.m + (x % self.ell) * self.m + y % self.m

    def shift(self, vector, dx, dy):
        return np.roll(vector.reshape(2, self.ell, self.m),
                       shift=(dx, dy), axis=(1, 2)).reshape(-1)

    def zx_dual(self, vector):
        """将 X(p,q) 映射为 Z(q^T,p^T) 对偶算符。"""
        a = vector.reshape(2, self.ell, self.m)
        return a[::-1][:, (-np.arange(self.ell)) % self.ell][:, :, (-np.arange(self.m)) % self.m].reshape(-1)

    def validate(self):
        rx, rz = rank(self.hx), rank(self.hz)
        assert not np.any((self.hx @ self.hz.T) % 2), 'CSS 对易条件失败'
        assert self.n - rx - rz == 12
        assert self.lx.shape == self.lz.shape == (12, self.n)
        assert not np.any((self.hz @ self.lx.T) % 2)
        assert not np.any((self.hx @ self.lz.T) % 2)
        assert rank((self.lx @ self.lz.T) % 2) == 12
        assert np.all(self.hx.sum(axis=1) == 6) and np.all(self.hz.sum(axis=1) == 6)
        return {'n': self.n, 'k': 12, 'paper_distance': self.distance,
                'rank_hx': rx, 'rank_hz': rz, 'check_weight': 6}


def make_code(name):
    if name not in ('gross', 'two_gross'):
        raise ValueError(name)
    ell, m, distance = (12, 6, 12) if name == 'gross' else (12, 12, 18)
    size = ell * m

    def polynomial_matrix(terms):
                                      
        matrix = np.zeros((size, size), dtype=np.uint8)
        for x in range(ell):
            for y in range(m):
                for dx, dy in terms:
                    matrix[x*m+y, ((x+dx) % ell)*m+(y+dy) % m] ^= 1
        return matrix

                                          
    a = polynomial_matrix([(0, 0), (0, 1), (3, -1)])
    b = polynomial_matrix([(0, 0), (1, 0), (-1, -3)])
    hx, hz = np.hstack([a, b]), np.hstack([b.T, a.T])
    lx = quotient_basis(hz, hx)
    lz = quotient_basis(hx, hz)
    code = BBCode(name, ell, m, distance, hx, hz, lx, lz)
    code.validate()
    return code


def paper_pivots(code):
    """返回论文式 (32)、(33) 给出的四个示例逻辑算符。"""
    if code.name == 'gross':
        p = [(4,0),(5,0),(6,1),(4,2),(5,4),(6,5)]
        q = [(3,0),(4,0),(3,1),(3,2),(4,2),(3,5)]
        r = [(0,0),(8,0),(1,1),(9,1),(3,4),(11,4)]
        s = [(1,0),(9,0),(4,4),(8,4),(0,5),(8,5)]
    else:
        p = [(2,0),(2,2),(8,2),(9,2),(3,3),(4,3),(7,4),(8,6),(6,7),(7,11)]
        q = [(3,2),(5,3),(7,3),(11,3),(8,4),(8,5),(6,7),(4,8),(1,9),(1,10)]
        r = [(4,2),(11,2),(0,5),(1,5),(5,5),(6,5),(1,8),(8,8),(2,11),(10,11)]
        s = [(x,y) for x in (2,11) for y in (6,9,10)] + [(8,7),(11,7),(5,8),(11,8)]

    def vec(left, right):
        v = np.zeros(code.n, dtype=np.uint8)
        for block, terms in enumerate((left, right)):
            for x, y in terms:
                v[code.index(block,x,y)] ^= 1
        return v

    x1, x7 = vec(p,q), vec(r,s)
    z1 = code.shift(code.zx_dual(x7), 1, 1)
    z7 = code.shift(code.zx_dual(x1), 1, 1)
    return x1, x7, z1, z7
