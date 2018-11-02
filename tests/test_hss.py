from hss import *

def test_test():
    print("I ran!")

def test_read_input_files():
    indir_small = "tests/testdata/input"
    indir_large = "tests/testdata/input_large"

    small_list = read_input_files(indir_small)
    large_list = read_input_files(indir_large)
