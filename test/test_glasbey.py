import os
from shutil import copyfile, move
from unittest import TestCase
from glasbey import Glasbey
import numpy


class TestGlasbey(TestCase):
    def setUp(self) -> None:
        file_path = os.path.dirname(os.path.realpath(__file__))
        self.test_palette = file_path + "/../palettes/set1.txt"
        self.test_palette_bkp = file_path + "/../palettes/set1.txt.bkp"

        assert os.path.isfile(self.test_palette)
        assert not os.path.isfile(self.test_palette_bkp)

    def tearDown(self) -> None:
        if os.path.isfile(self.test_palette_bkp):
            # do this in case a test failed
            move(self.test_palette_bkp, self.test_palette)

    def test_bad_path(self):
        with self.assertRaises(AssertionError):
            gb = Glasbey(base_palette="!!bad_path!!")

    def test_simple(self):
        gb = Glasbey(base_palette=self.test_palette)
        palette = gb.get_palette(size=1)
        self.assertTrue(palette.shape, numpy.array([[0, 0, 0]]).shape)

    def test_save_output(self):
        gb = Glasbey(base_palette=self.test_palette)
        palette = gb.get_palette(size=1)
        gb.save_palette(palette=palette, path="/tmp/random_glasbey_test_file.remove_me", format="byte", overwrite=True)

        self.assertEqual(['228,26,28\n'], open('/tmp/random_glasbey_test_file.remove_me', 'r').readlines())

    def test_extend_base_palette(self):
        self.assertEqual(9, len(open(self.test_palette, 'r').readlines()))  # sanity check

        gb = Glasbey(base_palette=self.test_palette)
        palette = gb.get_palette(size=10)

        self.assertEqual(10, len(palette))
        self.assertEqual(9, len(open(self.test_palette, 'r').readlines()))  # ensure there was no override

    def test_multiple_sequential_requests(self):
        gb = Glasbey(base_palette=self.test_palette)

        palette = gb.get_palette(size=5)
        self.assertEqual(5, len(palette))

        palette = gb.get_palette(size=15)
        self.assertEqual(15, len(palette))

        palette = gb.get_palette(size=20)
        self.assertEqual(20, len(palette))

        palette = gb.get_palette(size=18)
        self.assertEqual(18, len(palette))

    def test_overwrite_base_palette(self):
        copyfile(self.test_palette, self.test_palette_bkp)
        self.assertEqual(9, len(open(self.test_palette, 'r').readlines()))  # sanity check

        gb = Glasbey(base_palette=self.test_palette, overwrite_base_palette=True)
        palette = gb.get_palette(size=10)

        self.assertEqual(10, len(open(self.test_palette, 'r').readlines()))

        move(self.test_palette_bkp, self.test_palette)
