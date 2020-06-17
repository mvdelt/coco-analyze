from setuptools import setup
from Cython.Build import cythonize

setup(
    name='mask_pyx_j',
    ext_modules=cythonize(["_mask.pyx"]),
    zip_safe=False,
)