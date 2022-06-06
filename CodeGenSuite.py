import unittest
from TestUtils import TestCodeGen
from AST import *
import os, sys
from CodeGenerator import *
import subprocess

JASMIN_JAR = "./jasmin.jar"

class TestUtil:
    @staticmethod
    def makeSource(inputStr,num):
        filename = str(num) + ".txt"
        file = open(filename,"w")
        file.write(inputStr)
        file.close()

class TestCodeGen():
    @staticmethod
    def test(input, expect, num):
        asttree = input
        
        TestCodeGen.check("",asttree,num)
        
        dest = open(os.path.join(str(num), ".txt"),"r")
        line = dest.read()
        return line == expect

    @staticmethod
    def check(soldir,asttree,num):
        codeGen = CodeGenerator()
        path = os.path.join(soldir, str(num))
        if not os.path.isdir(path):
            os.mkdir(path)
        f = open(os.path.join(str(num), ".txt"),"w")
        try:
            codeGen.gen(asttree, path)
            
            subprocess.call("java  -jar "+ JASMIN_JAR + " " + path + "/D96Class.j",shell=True,stderr=subprocess.STDOUT)
            
            subprocess.run("java -cp ./lib:. D96Class",shell=True, stdout = f, timeout=10)
        except StaticError as e:
            f.write(str(e))
        except subprocess.TimeoutExpired:
            f.write("Time out\n")
        except subprocess.CalledProcessError as e:
            raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
        finally:
            f.close()

class CheckCodeGenSuite(unittest.TestCase):
    def test_int_ast(self):
        input = Program([ClassDecl(Id('Program'), [MethodDecl(Static(), Id('main'), [], Block([]))])])
        expect = ''
        self.assertTrue(TestCodeGen.test(input, expect, 1))

a = CheckCodeGenSuite().test_int_ast()
