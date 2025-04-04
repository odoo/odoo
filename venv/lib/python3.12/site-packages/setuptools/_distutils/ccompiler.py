from .compilers.C import base
from .compilers.C.base import (
    CompileError,
    LinkError,
    gen_lib_options,
    gen_preprocess_options,
    get_default_compiler,
    new_compiler,
    show_compilers,
)

__all__ = [
    'CompileError',
    'LinkError',
    'gen_lib_options',
    'gen_preprocess_options',
    'get_default_compiler',
    'new_compiler',
    'show_compilers',
]


CCompiler = base.Compiler
