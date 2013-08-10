import unittest

import imageproxy


class TestConfig(unittest.TestCase):

    def test_read(self):
        defaults = (
            '[section]\n'
            'hello=world\n'
        )
        conf = imageproxy.read_config(defaults)
        self.assertEqual(conf.sections(), ['section'])
        self.assertEqual(conf.items('section'), [('hello', 'world')])


if __name__ == '__main__':
    unittest.main()
