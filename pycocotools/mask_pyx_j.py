from setuptools import setup
from Cython.Build import cythonize
import numpy

setup(
    name='mask_pyx_j',
    ext_modules=cythonize(["/content/cocoAnalyze/pycocotools/_mask.pyx"]),
    include_dirs=[numpy.get_include()],
    zip_safe=False,
)