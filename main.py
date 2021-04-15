import requests

import importTest
import extras

def helloWorld():
  print('hello world')

if __name__=="__main__":
  helloWorld()
  importTest.hello.helloFoo()
  extras.extraFunction()
