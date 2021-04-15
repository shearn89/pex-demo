# Creating a PEX binary from Python scripts #

This tutorial walks through creating a self-contained PEX binary from a set of
python scripts. The main reason I wrote this is that Python 2 is now end-of-life,
so we should be writing Python 3 scripts. However, Python3 on Centos 7 is old,
and if you're working offline then you may not have access to pip. Also, spraying
Pip dependencies across your system is not really a great idea: if we can package
everything up so that it only depends on Python 3 and not on lots of other 
libraries, the situation is more manageable!

# Inital basic setup #

First we create our repo with a very basic script.

```
$ mkdir pex-test
$ cd pex-test
$ pip install --user virtualenv
$ virtualenv .venv
$ source .venv/bin/activate
$ pip install pex
```

Then, we can create our simple hello world script. It'll pull in the `requests`
library, but it doesn't actually use it. It's just to demonstrate pulling deps
from pypi.

```
$ cat <EOF>>main.py
import requests

def hello():
  print('hello world')

if __name__=="__main__":
  hello()
EOF
```

Then we set up the `requirements` file:

```
$ echo 'requests' > requirements.txt
$ pip install -r requirements.txt
```

...and then we test our script:

```
$ python main.py
hello world
```

We can see it work! However, we want it to be a PEX file.

# Building the PEX file #

PEX requires things to be modules for them to get bundled in, so we need to create a `setup.py` file:

```
$ cat <EOF>>setup.py
from distutils.core import setup
setup(
  name='pexTest',
  version='1.0',
  scripts=['main.py'],
)
EOF
```

Now, we can attempt to create our binary and see if it works:

```
pex . -r requirements.txt -c main.py -o test.pex
./test.pex
hello world
```

It works! A good start. Lets make it more complicated and add some other modules/packages.

# Adding Modules #

We'll create a simple package and add some very simple extra modules & methods to it.

```
$ mkdir importTest
$ touch importTest/__init__.py
$ cat <EOF>>importTest/hello.py
def helloFoo():
  print("hello foo")
EOF
```

Now, update `main.py` to pull in the new file:

```
import requests

from importTest import hello

def helloWorld():
  print('hello world')

if __name__=="__main__":
  helloWorld()
  hello.helloFoo()
```

If we run the script, we should now see it call the extra method:

```
$ python main.py
hello world
hello foo
```

So, lets build and test our pex again:

```
$ pex . -r requirements.txt -c main.py -o test.pex
$ ./test.pex
Traceback (most recent call last):
  File "/home/shearna/repos/pex-test-2/test.pex/.bootstrap/pex/pex.py", line 483, in execute
  File "/home/shearna/repos/pex-test-2/test.pex/.bootstrap/pex/pex.py", line 400, in _wrap_coverage
  File "/home/shearna/repos/pex-test-2/test.pex/.bootstrap/pex/pex.py", line 431, in _wrap_profiling
  File "/home/shearna/repos/pex-test-2/test.pex/.bootstrap/pex/pex.py", line 537, in _execute
  File "/home/shearna/repos/pex-test-2/test.pex/.bootstrap/pex/pex.py", line 621, in execute_script
  File "/home/shearna/repos/pex-test-2/test.pex/.bootstrap/pex/pex.py", line 649, in execute_content
  File "/home/shearna/repos/pex-test-2/test.pex/.bootstrap/pex/compatibility.py", line 93, in exec_function
  File "/home/shearna/.pex/installed_wheels/9784003ee198c2861b363bff417a1ea591d2c659/pexTest-1.0-py3-none-any.whl/bin/main.py", line 3, in <module>
    from importTest import hello
ModuleNotFoundError: No module named 'importTest'
```

Aha! We need to update `setup.py` to add in the new package we've created. Open up the file and add the packages line:

```
from distutils.core import setup
setup(
  name='pexTest',
  version='1.0',
  packages=['importTest'],
  scripts=['main.py'],
)
```

Now if we build and test it:

```
$ pex . -r requirements.txt -c main.py -o test.pex && ./test.pex
hello world
hello foo
```

Effectively, things have to be packages!

# Packages with Multiple Modules #

My python was a bit rusty when I wrote this, so this tripped me up. If you're more 
familiar with Python and how it loads modules, you might already know this. I'm 
adding the info here for future personal reference, or for googlers who stop by.

Let's now add another module `goodbye` to our package.

```
$ cat <EOF>>importTest/goodbye.py
def goodbye():
  print("goodbye")
EOF
```

Then update `importTest/hello.py`:

```
import goodbye
def helloFoo():
  print("hello foo")
  goodbye.goodbye()

if __name__=="__main__":
  helloFoo()
```

And run it to test:

```
$ python importTest/hello.py
hello foo
goodbye
```

But, if we run the same thing from `main`:

```
$ python main.py
Traceback (most recent call last):
  File "main.py", line 3, in <module>
    from importTest import hello
  File "/home/shearna/repos/pex-test-2/importTest/hello.py", line 1, in <module>
    import goodbye
ModuleNotFoundError: No module named 'goodbye'
```

So how do we fix this? First I tried to update `__init__.py` to include the 
script in the package:

```
$ echo 'from importTest import hello,goodbye' > importTest/__init__.py
```

But that still didn't work. What about importing the whole package in main.py?

```
import requests

import importTest

def helloWorld():
  print('hello world')

if __name__=="__main__":
  helloWorld()
  importTest.hello.helloFoo()
```

But that also didn't work! Okay, let's try using the from-import
syntax in hello.py:

```
$ cat importTest/hello.py
from importTest import goodbye

def helloFoo():
  print("hello foo")
  goodbye.goodbye()

if __name__=="__main__":
  helloFoo()
```

...and test:

```
$ python main.py
hello world
hello foo
goodbye
```

Aha! I have to admit I'm not 100% clear on this, but it's to do with how python 
loads modules/packages.
[More info here](https://stackoverflow.com/questions/36515197/python-import-module-from-a-package)

So then the pex file:

```
$ pex . -r requirements.txt -c main.py -o test.pex && ./test.pex
hello world
hello foo
goodbye
```

Okay, good! So, general lesson seems to be that if you want to run your scripts
as pex files, they need to be well-formed pacakages/modules first, not just a
bunch of python files!

# Adding in non-packaged scripts #

Lastly, if you **do** want to have top-level scripts, you just need to add them as
modules in setup.py:

```
cat <EOF>>extras.py
def extraFunction():
  print("hello from the extra function")
EOF
```

Update `main`:

```
$ cat main.py
import requests

import importTest
import extras

def helloWorld():
  print('hello world')

if __name__=="__main__":
  helloWorld()
  importTest.hello.helloFoo()
  extras.extraFunction()
```

Now update `setup.py` and add the `py_modules` line:

```
$ cat setup.py
from distutils.core import setup
setup(
  name='pexTest',
  version='1.0',
  py_modules=['extras'],
  packages=['importTest'],
  scripts=['main.py'],
)
```

Then test and run:

```
$ python main.py
hello world
hello foo
goodbye
hello from the extra function
```

Which is good! So finally:

```
$ pex . -r requirements.txt -c main.py -o test.pex && ./test.pex
hello world
hello foo
goodbye
hello from the extra function
```

# Conclusion #

Hopefully this has helped someone! If not, at least it's here for my own reference.
I find this is the sort of task I do a few times on a project but then don't have to
do again for ages, and I always forget the details...
