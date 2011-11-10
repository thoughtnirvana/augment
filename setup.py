"""
Augment
-------

Python decorators for contracts and augmenting OOP.
from distutils.core import setup


Contracts.
``````````

The syntax below should be self explanatory. It can be applied both to bound and unbound methods.

::

    # Constraints on passed arguments.
    # Constraints can be callables or regular expressions.
    # Throws a `TypeError` by default if contraints are violated.
    # Optionally, an error handler can be specified which receives the errors.
    @ensure_args(a=lambda x: x > 10,
                 b=r'^?-\d+(\.\d+)$',
                 c=lambda x: x < 5) # `c` will be picked from `kwargs`.
    def foo(a, b, **kwargs):
        pass

    # Ensure at least one of the constraints is true.
    @ensure_one_of(a=lambda x: x, b=lambda x: x)
    def foo(a, b):
        pass

    # Ensures only one of the constraints is true.
    @ensure_one_of(exclusive=True, c=lambda x: x, d=lambda x: x)
    def foo(a, b):
        pass

    # Transform arguments.
    @transform_args(a=lambda x: x * x)
    def foo(a):
        pass

    # Bundling multiple constraints.
    # Contracts run in inside out order
    # i.e the one right above function will run first.
    # In this case, `@ensure_args...` will be the first to run.
    @transform_args(a=lambda x: x * x)
    @ensure_one_of(c=lambda x: x, d=lambda x: x)
    @ensure_args(a=lambda x: x > 10,
                b=lambda x: hasattr(x, '__getitem__'),
                c=lambda x: x < 5)
    def foo(a, b, c=4, d=None):
        pass


Function/method hooks.
``````````````````````

Basic function hooks to run on entering, leaving or both ways.

::

    def login(root):
        print "Logging in."

    def logout(root):
        print "Logging out"

    # `login` will run before entering `home`.
    # `logout` will run after exiting from `home`.
    # `root` param passed to `home` will be passed to `login`, `logout`.
    @enter(login)
    @leave(logout)
    def home(root):
        print "Home page."


    def tracer():
        print "tracing"

    # `tracer` will run both before entering `home` and after
    # exiting `home`.
    @around(tracer)
    def inbox():
        print "Inbox"

Please note that the hooks(`login` and `logout`) above are passed the arguments passed to the wrapped method(`home`).

Method hooks should be accepting the same arguments as wrapped method.


They work the same on bound functions.

::
    class Foo:
        def login(self):
            print "Logging in."

        def logout(self):
            print "Logging out"

        @leave(logout)
        @enter(login)
        def home(self, test=None):
            print "Home page."

        def tracer(self):
            print "tracing"

        @around(tracer)
        def inbox(self):
            print "Inbox"


Dynamic delgation.
``````````````````

::

    class Foo:
        def __init__(self):
            self.a = 'a'
            self.b = 'b'
            self.c = 'c'

    @delegate_to('foo_delegate', 'a', 'b')
    class Bar:
        def __init__(self):
            self.foo_delegate = Foo()
    b = Bar()
    # `a` and `b` will be delegated to `Foo`.
    print b.a
    print b.b
    # This will throw an AttributeError.
    print b.c

"""

from setuptools import setup
setup(name='Augment',
      version='0.2',
      description='Python decorators for contracts and augmenting OOP.',
      long_description=__doc__,
      author='Rahul Kumar',
      author_email='rahul@thoughtnirvana.com',
      license='BSD',
      url='https://github.com/thoughtnirvana/augment',
      py_modules=['augment']
     )
