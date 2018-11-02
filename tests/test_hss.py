from ..hss import *

def test_read_input_files():
    indir_small = "tests/testdata/input"
    small_list = read_input_files(indir_small)
    assert len(small_list) == 8
    assert type(small_list[0]) == pymarc.Record

def test_get_institution_dict():
    d = get_institution_dict()
    assert type(d) == dict
    assert len(d) > 0

def test_get_inst_code():
    assert get_inst_code("UNI for LIFE") == ("ioo:UG:UL", "")
    assert get_inst_code("NN") == (None, None)
