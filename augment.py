"""
General purpose decorators and other utilities for contract based programming and oop
augmentation.
"""
import re
from functools import wraps

def _get_args_and_name(fn):
    """
    Returns `(args, name)` where `args` are names of positional
    arguments `fn` takes and `name` is `fn.__name__`

    >>> def foo(a, b, c=2, *args, **kwargs):
    ...     pass
    ...
    >>> _get_args_and_name(foo)
    (('a', 'b', 'c'), 'foo')

    """
    allargs, fn_name = getattr(fn, '__allargs__', None), \
            getattr(fn, '__fnname__', None)
    if not allargs:
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
    ...              b=r'^-?\d+(\.\d+)?$',
    ...              c=lambda x: x < 10)
    ... def foo(a, b, **kwargs):
    ...     pass
    ...
    >>> foo(9, '12') #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. 'a = 9' violates constraint.
    >>> foo(11, '12')
    >>> foo(11, '12', 11) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: foo() takes exactly 2 arguments (3 given)
    >>> foo(11, 'ab', 11) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. 'b = ab' violates constraint.
    >>> foo(11, 'ab') #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. 'b = ab' violates constraint.
    """
    def decorator(fn):
        allargs, fn_name = _get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = _check_args(rules, pargs, args, kwargs)
            errors = []
            for arg_name, arg_val, valid in results:
                if not valid:
                    errors.append("'%s = %s' violates constraint %s. "
                                  % (arg_name, arg_val, rules[arg_name]))
            if errors:
                fn_info = "Errors in '%s'. " % fn_name
                errors.insert(0, fn_info)
                _propogate_error(''.join(errors), error_handler)
            else:
                return fn(*args, **kwargs)
        wrapper.__allargs__, wrapper.__fnname__ = allargs, fn_name
        return wrapper
    return decorator

def _check_args(rules, pargs, args, kwargs):
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
            validator = lambda val: re.match(constraint, str(val))
        if arg_val:
            results.append((arg_name, arg_val, validator(arg_val)))
    return results

def ensure_one_of(error_handler=None, exclusive=False, **rules):
    """
    `rules` is a dictionary of `arg_name=1` pairs.
    Ensures at least(or at most depending on `exclusive)` one of `arg_name`
    is passed and not null.

    >>> @ensure_one_of(a=lambda x: x > 10, b=lambda x: x < 10)
    ... def foo(a, b):
    ...     pass
    ...
    >>> foo(9, 9)
    >>> foo(9, 11) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. One of '['a', 'b']' must validate.
    >>> @ensure_one_of(exclusive=True, a=lambda x: x > 10, b=lambda x: x < 10)
    ... def foo(a, b):
    ...     pass
    ...
    >>> foo(9, 11) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. One of '['a', 'b']' must validate.
    >>> foo(9, 9)
    >>> foo(11, 11)
    >>> foo(11, 9) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    TypeError: Errors in 'foo'. Only one of '['a', 'b']' must validate.
    """
    def decorator(fn):
        allargs, fn_name = _get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = _check_args(rules, pargs, args, kwargs)
            valid_count = len([valid for arg_name, arg_val, valid in results
                                if valid])
            fn_info = "Errors in '%s'. " % fn_name
            if valid_count < 1:
                error_msg = "One of '%s' must validate. Constraints: %s" % \
                        (rules.keys(), rules)
                _propogate_error(fn_info + error_msg, error_handler)
            elif valid_count > 1 and exclusive:
                error_msg = "Only one of '%s' must validate. Constraints: %s" % \
                        (rules.keys(), rules)
                _propogate_error(fn_info + error_msg, error_handler)
            else:
                return fn(*args, **kwargs)
        wrapper.__allargs__, wrapper.__fnname__ = allargs, fn_name
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
        allargs, fn_name = _get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = _check_args(rules, pargs, args, kwargs)
            args = list(args)
            for arg_name, arg_val, res in results:
                if arg_name in kwargs:
                    kwargs[arg_name] = res
                elif arg_name in pargs:
                    args[pargs.index(arg_name)] = res
                return fn(*args, **kwargs)
        wrapper.__allargs__, wrapper.__fnname__ = allargs, fn_name
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
        allargs, fn_name = _get_args_and_name(fn)
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
        wrapper.__allargs__, wrapper.__fnname__ = allargs, fn_name
        return wrapper
    return decorator

def enter(aux_fn):
    """
    Decorator for installing a function hook which runs before a given
    function.

    >>> def login(a): print "Logging in. Received param %s" % a
    ...
    >>> @enter(login)
    ... def home(a): print "home"
    ...
    >>> home(5)
    Logging in. Received param 5
    home
    """
    return _surround(aux_fn, before=True)

def leave(aux_fn):
    """
    Decorator for installing a function hook which runs after a given
    function.

    >>> def logout(a): print "Logging out. Received param %s" % a
    ...
    >>> @leave(logout)
    ... def home(a): print "home"
    ...
    >>> home(5)
    home
    Logging out. Received param 5
    """
    return _surround(aux_fn, after=True)

def around(aux_fn):
    """
    Decorator for installing a function hook which runs before and after
    a given function.

    >>> def login(a): print "Logging in. Received param %s" % a
    ...
    >>> def logout(a): print "Logging out. Received param %s" % a
    ...
    >>> @leave(logout)
    ... @enter(login)
    ... def home(a): print "home"
    ...
    >>> home(5)
    Logging in. Received param 5
    home
    Logging out. Received param 5

    >>> def trace(a): print "Tracing home"
    ...
    >>> @around(trace)
    ... def home(a): print "home"
    ...
    >>> home(5)
    Tracing home
    home
    Tracing home
    """
    return _surround(aux_fn, around=True)

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
    >>> b.c #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
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

if __name__ == '__main__':
    import doctest
    doctest.testmod()
