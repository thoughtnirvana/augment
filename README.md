### augment - Misc. python decorators.

#### Installation 

    pip install augment

#### Examples

Some specific examples are list below. Tests contain more exmaples.


    class TestAugment(unittest.TestCase):
        def test_ensure_args(self):
            # Define constrained function.
            @ensure_args(a=(lambda x: x > 10, 'must be greater than 10'),
                        b=(lambda x: x < 10, 'must be smaller than 10'),
                        c=(r'^-?\d+(\.\d+)?$', 'must be a valid number'))
            def fn(a, b, **kwargs):
                return (a, b)
            # Check for violation.
            try:
                fn(5, 11, c='c')
            except AugmentError, ex:
                self.assertEqual(ex.errors['a'], ['must be greater than 10'])
                self.assertEqual(ex.errors['b'], ['must be smaller than 10'])
                self.assertEqual(ex.errors['c'], ['must be a valid number'])
            # Check for partial errors.
            try:
                fn(11, 5)
            except AugmentError, ex:
                self.assertFalse(ex.errors['a'])
                self.assertEqual(ex.errors['b'], ['must be smaller than 10'])
            # Check successful call.
            self.assertEqual(fn(11, 5), (11, 5))

        def test_ensure_one_of(self):
            # Define constrained function.
            @ensure_one_of(a=(lambda x: x > 10, 'must be greater than 10'),
                        b=(lambda x: x < 10, 'must be smaller than 10'))
            def fn(a, b):
                return (a, b)
            # Check for violation when both constraints are incorrect.
            try:
                fn(5, 11)
            except AugmentError, ex:
                self.assertEqual(ex.errors['a'], ['must be greater than 10'])
                self.assertEqual(ex.errors['b'], ['must be smaller than 10'])
            # Check successful call when one of the arguments validates.
            self.assertEqual(fn(11, 11), (11, 11))
            # Check successful call when all arguments validate.
            self.assertEqual(fn(11, 5), (11, 5))

        def test_ensure_one_of_exclusive(self):
            # Define constrained function.
            @ensure_one_of(exclusive=True, a=(lambda x: x > 10, 'must be greater than 10'),
                        b=(lambda x: x < 10, 'must be smaller than 10'))
            def fn(a, b):
                return (a, b)
            # Check for violation when both constraints are incorrect.
            try:
                fn(5, 11)
            except AugmentError, ex:
                self.assertEqual(ex.errors['a'], ['must be greater than 10'])
                self.assertEqual(ex.errors['b'], ['must be smaller than 10'])
            # Check successful call when one of the arguments validates.
            self.assertEqual(fn(11, 11), (11, 11))
            # Check violation when all arguments validate.
            self.assertRaises(AugmentError, fn, 11, 5)

        def test_transform_arg(self):
            @transform_args(a=lambda x: x * x)
            def fn(a):
                return a
            self.assertEqual(fn(5), 25)



##### Contracts.

The syntax below should be self explanatory. It can be applied both to bound and unbound methods.

    # Constraints on passed arguments.
    # Constraints can be callables or regular expressions.
    # Throws a `AugmentError` by default if contraints are violated.
    # Optionally, an error handler can be specified which receives the errors.
    @ensure_args(a=(lambda x: x > 10, 'must be greater than 10'),
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
    # Contracts run in top down order 
    # i.e the top most will run first. 
    # In this case, `@transform_args...` will be the first to run.
    @transform_args(a=lambda x: x * x)
    @ensure_one_of(c=lambda x: x, d=lambda x: x)
    @ensure_args(a=lambda x: x > 10,
                b=lambda x: hasattr(x, '__getitem__'),
                c=lambda x: x < 5)
    def foo(a, b, c=4, d=None):
        pass


##### Function/method hooks.

Basic function hooks to run on entering, leaving or both ways.


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


##### Dynamic delgation.


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
