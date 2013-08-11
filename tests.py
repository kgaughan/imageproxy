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

    def test_parse_defaults(self):
        # This test assumes that IMAGEPROXY_SETTINGS isn't set.
        sites, types = imageproxy.load_config()

        self.assertTrue(isinstance(sites, dict))
        self.assertEqual(len(sites), 0)

        self.assertTrue(isinstance(types, dict))
        self.assertEqual(sorted(types.keys()),
                         ['image/gif', 'image/jpeg', 'image/png'])

        self.assertFalse(types['image/gif']['resize'])
        self.assertEqual(types['image/gif']['suffixes'], ['gif'])

        self.assertTrue(types['image/jpeg']['resize'])
        self.assertEqual(types['image/jpeg']['suffixes'],
                         ['jpeg', 'jpg', 'jpe'])

    def test_parse_site(self):
        defaults = (
            '[site:example.com]\n'
            'cache=true\n'
            'prefix=/media\n'
            'root=/dev/null\n'
        )
        conf = imageproxy.read_config(defaults)
        sites, types = imageproxy.parse_config(conf)

        self.assertTrue(isinstance(types, dict))
        self.assertEqual(len(types), 0)

        self.assertEqual(sites.keys(), ['example.com'])
        self.assertEqual(sites['example.com'], {'cache': True,
                                                'prefix': '/media',
                                                'root': '/dev/null'})


if __name__ == '__main__':
    unittest.main()
