"""
General purpose decorators and other utilities for contract based programming and oop
augmentation.
"""
import re, sys
from inspect import getouterframes, currentframe
from functools import wraps

def get_args_and_name(fn):
    """
    Returns `(args, name)` where `args` are names of positional
    arguments `fn` takes and `name` is `fn.__name__`

    >>> def foo(a, b, c=2, *args, **kwargs):
    ...     pass
    ...
    >>> get_args_and_name(foo)
    (('a', 'b', 'c'), 'foo')

    """
    code = fn.func_code
    allargs = code.co_varnames[:code.co_argcount]
    fn_name = fn.__name__
    return allargs, fn_name

def _propogate_error(errors, handler=None, exception_type=TypeError):
    """
    Passes the errors to the handler or raises an exception.
    """
    if handler:
        return handler(errors)
    else:
        raise exception_type(errors)

def ensure_args(error_handler=None, **rules):
    """
    Ensures the value of `arg_name` satisfies `constraint`
    where `rules` is a collection of `arg_name=constraint`.

    >>> @ensure_args(a=lambda x: x > 10,
    ...              b=r'^-?\d+(\.\d+)$',
    ...              c=lambda x: x)
    ... def foo(a, b, **kwargs):
    ...     pass
    ...
    >>> foo(11, '12', c=4)
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. 'b = 12' violates constraint.

    >>> foo(11, '12.2', c=4)
    >>> foo(9, '12.2', c=4)
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. 'a = 9' violates constraint.
    """
    def decorator(fn):
        fn = getattr(fn, '__wrapped__', fn)
        allargs, fn_name = get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = check_args(rules, pargs, args, kwargs)
            errors = []
            for arg_name, arg_val, valid in results:
                if not valid:
                    errors.append("'%s = %s' violates constraint. "
                                  % (arg_name, arg_val))
            if errors:
                fn_info = "Errors in '%s'. " % fn_name
                errors.insert(0, fn_info)
                _propogate_error(''.join(errors))
            else:
                return fn(*args, **kwargs)
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator

def check_args(rules, pargs, args, kwargs):
    """
    Checks that `arg_val` satisfies `constraint` where `rules` is a
    dicionary of `arg_name=constraint` and `arg_val` is in `kwargs` or `args`
    """
    results = []
    for arg_name, constraint in rules.iteritems():
        # Get the argument value.
        arg_val = None
        if kwargs.get(arg_name):
            arg_val = kwargs[arg_name]
        elif arg_name in pargs:
            arg_val = args[pargs.index(arg_name)]
        # `constraint` can either be a regex or a callable.
        validator = constraint
        if not callable(constraint):
            validator = lambda val: re.match(constraint, val)
        if arg_val:
            results.append((arg_name, arg_val, validator(arg_val)))
    return results

def ensure_one_of(exclusive=False, **rules):
    """
    `rules` is a dictionary of `arg_name=1` pairs.
    Ensures at least(or at most depending on `exclusive)` one of `arg_name`
    is passed and not null.

    >>> foo(9, 9)
    >>> @ensure_one_of(a=lambda x: x > 10, b=lambda x: x < 10)
    ... def foo(a, b):
    ...     pass
    ...
    >>> foo(9, 11)
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. One of '['a', 'b']' must validate.

    >>> @ensure_one_of(exclusive=True, a=lambda x: x > 10, b=lambda x: x < 10)
    ... def foo(a, b):
    ...     pass
    ...
    >>> foo(9, 11)
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. One of '['a', 'b']' must validate.

    >>> foo(9, 9)
    >>> foo(11, 11)
    >>> foo(11, 9)
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. Only one of '['a', 'b']' must validate.
    """
    def decorator(fn):
        fn = getattr(fn, '__wrapped__', fn)
        allargs, fn_name = get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = check_args(rules, pargs, args, kwargs)
            valid_count = len([valid for arg_name, arg_val, valid in results
                                if valid])
            fn_info = "Errors in '%s'. " % fn_name
            if valid_count < 1:
                error_msg = "One of '%s' must validate." % rules.keys()
                _propogate_error(fn_info + error_msg)
            elif valid_count > 1 and exclusive:
                error_msg = "Only one of '%s' must validate." % rules.keys()
                _propogate_error(fn_info + error_msg)
            else:
                return fn(*args, **kwargs)
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator

def transform_args(**rules):
    """
    Transform the value of `arg_name`
    where `rules` is a collection of `arg_name=transformation`.

    >>> @transform_args(a=lambda x: x*x)
    ... def foo(a):
    ...     print a
    ...
    >>> foo(2)
    4
    """
    def decorator(fn):
        fn = getattr(fn, '__wrapped__', fn)
        allargs, fn_name = get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = check_args(rules, pargs, args, kwargs)
            errors = []
            args = list(args)
            for arg_name, arg_val, res in results:
                if arg_name in kwargs:
                    kwargs[arg_name] = res
                elif arg_name in pargs:
                    args[pargs.index(arg_name)] = res
                return fn(*args, **kwargs)
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator

@ensure_one_of(exclusive=True, around=lambda x: x,
               before=lambda x: x,
               after=lambda x: x)
def _surround(aux_fn, around=False, before=False, after=False):
    """
    Runs `aux_fn` before/after/around `fn`.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if around:
                aux_fn(*args, **kwargs)
                fn(*args, **kwargs)
                return aux_fn(*args, **kwargs)
            elif before:
                aux_fn(*args, **kwargs)
                return fn(*args, **kwargs)
            elif after:
                fn(*args, **kwargs)
                return aux_fn(*args, **kwargs)
        return wrapper
    return decorator

enter = lambda aux_fn: _surround(aux_fn, before=True)
leave = lambda aux_fn: _surround(aux_fn, after=True)
around = lambda aux_fn: _surround(aux_fn, around=True)

def delegate_to(target, *attribs):
    """
    Delegates `attribs` access to `target` for given `cls`.

    >>> class Foo:
    ...     def __init__(self):
    ...         self.a = 10
    ...         self.b = 20
    ...         self.c = 30
    ...
    >>> @delegate_to('foo_delegate', 'a', 'b')
    ... class Bar:
    ...     def __init__(self):
    ...         self.foo_delegate = Foo()
    ...
    >>> b = Bar()
    >>> b.a
    10
    >>> b.b
    20
    >>> b.c
    ------------------------------------------------------------
    Traceback (most recent call last):
    File "<ipython console>", line 1, in <module>
    File "augment.py", line 204, in __getattr__
    AttributeError: No such attribute: c
    """
    def decorator(cls):
        class Wrapper:
            def __init__(self, *args, **kwargs):
                wrapped_cls = cls(*args, **kwargs)
                self.target = getattr(wrapped_cls, target)

            def __getattr__(self, attr_name):
                if attr_name in attribs:
                    return getattr(self.target, attr_name)
                raise AttributeError("No such attribute: %s" % attr_name)
        return Wrapper
    return decorator
