import unittest
from augment import (AugmentError, ensure_args, ensure_one_of, transform_args)

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


if __name__ == '__main__':
    unittest.main()
