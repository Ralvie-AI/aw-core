from pathlib import Path
import os

from setuptools import setup, Extension
from Cython.Build import cythonize

BASE = Path(__file__).resolve().parent
os.chdir(BASE)

extensions = [
    Extension("salt_file", ["salt_file.pyx"]),
    Extension("secure", ["secure.py"]),
    Extension("cache", ["cache.py"]),
    Extension("os_util", ["os_util.py"]),
    Extension("db_cache", ["db_cache.py"]),
    Extension("const", ["const.py"]),
    Extension("system_uuid", ["system_uuid.py"]),
    Extension("util", ["util.py"]),
]


setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    )
)