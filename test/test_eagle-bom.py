from subprocess import call
import filecmp
import sys

simple_sch = "blink1_v1a.sch"
simple_sch_csv = "blink1_v1a_sch.csv"

simple_brd = "blink1_v1a.brd"
simple_brd_csv = "blink1_v1a_brd.csv"

def test_simple_sch():

    #test sch > bom way
    try:
        retcode = call("python eagle-bom.py" + " --sch=test/files/" + simple_sch + " --csv=/tmp/simple.csv", shell=True)
        assert retcode == 0
    except OSError as e:
        assert 0

    assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_sch_csv) 
    
def test_simple_brd(): 
    #test brd > bom way
    try:
        retcode = call("python eagle-bom.py" + " --brd=test/files/" + simple_brd + " --csv=/tmp/simple.csv", shell=True)
        assert retcode == 0
    except OSError as e:
        assert 0

    assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_brd_csv) 

def test_cli():
    try:
        #call script with garbage parameters
        retcode = call("python eagle-bom.py" + " --foobar", shell=True)
        assert retcode == 2
        #call script without input file
        retcode = call("python eagle-bom.py --csv=/tmp/simple.csv", shell=True)
        assert retcode == 3
        #call script without output file
        retcode = call("python eagle-bom.py" + " --brd=test/files/" + simple_brd, shell=True)
        assert retcode == 4
        #try to pass an invalid output type
        retcode = call("python eagle-bom.py" + " --brd=test/files/" + simple_brd + " --csv=/tmp/simple.csv -t foobar", shell=True)
        assert retcode == 5
        #TODO: add more cli tests
    except OSError as e:
        assert 0

