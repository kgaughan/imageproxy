import unittest

import imageproxy


class TestConfig(unittest.TestCase):
    def test_read(self):
        defaults = "[section]\n" "hello=world\n"
        conf = imageproxy.read_config(defaults)
        self.assertEqual(conf.sections(), ["section"])
        self.assertEqual(conf.items("section"), [("hello", "world")])

    def test_parse_defaults(self):
        # This test assumes that IMAGEPROXY_SETTINGS isn't set.
        sites, types = imageproxy.load_config()

        self.assertTrue(isinstance(sites, dict))
        self.assertEqual(len(sites), 0)

        self.assertTrue(isinstance(types, dict))
        self.assertEqual(sorted(types.keys()), ["image/jpeg"])
        self.assertTrue(types["image/jpeg"])

    def test_parse_site(self):
        defaults = "[site:example.com]\ncache=true\nprefix=/media\nroot=/dev/null\n"
        conf = imageproxy.read_config(defaults)
        sites, types = imageproxy.parse_config(conf)

        self.assertTrue(isinstance(types, dict))
        self.assertEqual(len(types), 0)

        self.assertEqual(list(sites.keys()), ["example.com"])
        self.assertEqual(
            sites["example.com"],
            {
                "cache": True,
                "dimensions": {64, 256, 320, 640},
                "prefix": "/media",
                "root": "/dev/null",
                "directories": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
