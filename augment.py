"""
General purpose decorators and other utilities for contract based programming and oop
augmentation.
"""
import re
from functools import wraps
from collections import defaultdict

class AugmentError(ValueError):
    """
    Default exception raised when a contraint is voilated.
    """
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        """
        Dumps the `self.errors` dictionary.
        """
        return repr(self.errors)

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

def _propogate_error(errors, handler=None, exception_type=AugmentError):
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
    where `rules` is a collection of `arg_name=constraint` or `arg_name=(constraint, message)`
    where `message` is the voilation message.
    """
    def decorator(fn):
        allargs, fn_name = _get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = _check_args(rules, pargs, args, kwargs)
            errors = _construct_errors(results, rules)
            if errors:
                plural = 'errors' if len(errors) > 1 else 'error'
                fn_info = '%s: %s %s.' % (fn_name, len(errors), plural)
                errors['base'].append(fn_info)
                _propogate_error(errors, error_handler)
            else:
                return fn(*args, **kwargs)
        wrapper.__allargs__, wrapper.__fnname__ = allargs, fn_name
        return wrapper
    return decorator

def _construct_errors(results, rules):
    """
    Constructs errors dictionary from the returned results.
    """
    errors = defaultdict(list)
    for res in results:
        if len(res) == 4:
            arg_name, arg_val, valid, message = res
        else:
            arg_name, arg_val, valid = res
        if not valid:
            if not message:
                # No user supplied message. Construct a generic message.
                message = '"%s" violates constraint "%s."' % (arg_val, rules[arg_name])
            errors[arg_name].append(message)
    return errors

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
        message = None
        if isinstance(constraint, list) or isinstance(constraint, tuple):
            if len(constraint) == 2:
                constraint, message = constraint
            else:
                raise ValueError('Constraints can either be "(constraint, message)" or "constraint"'
                                 '"%s" is in inproper format' % constraint)
        # `constraint` can either be a regex or a callable.
        validator = constraint
        if not callable(constraint):
            validator = lambda val: re.match(constraint, str(val))
        if arg_val:
            if message:
                results.append((arg_name, arg_val, validator(arg_val), message))
            else:
                results.append((arg_name, arg_val, validator(arg_val)))
    return results

def ensure_one_of(error_handler=None, exclusive=False, **rules):
    """
    `rules` is a dictionary of `arg_name=1` pairs.
    Ensures at least(or at most depending on `exclusive)` one of `arg_name`
    is passed and not null.
    """
    def decorator(fn):
        allargs, fn_name = _get_args_and_name(fn)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pargs = list(allargs)[:len(args)]
            results = _check_args(rules, pargs, args, kwargs)
            errors = _construct_errors(results, rules)
            if errors:
                valid_count = len(rules) - len(errors)
                if valid_count < 1:
                    errors['base'].append('%s: One of constraints must validate.' % fn_name)
                    return _propogate_error(errors, error_handler)
                elif valid_count > 1 and exclusive:
                    errors['base'].append('%s: Only one of constraints should validate.' % fn_name)
                    return _propogate_error(errors, error_handler)
                else:
                    return fn(*args, **kwargs)
            else:
                if exclusive:
                    errors['base'].append('%s: Only one of constraints should validate.' % fn_name)
                    return _propogate_error(errors, error_handler)
                else:
                    return fn(*args, **kwargs)
        wrapper.__allargs__, wrapper.__fnname__ = allargs, fn_name
        return wrapper
    return decorator

def transform_args(**rules):
    """
    Transform the value of `arg_name`
    where `rules` is a collection of `arg_name=transformation`.
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
