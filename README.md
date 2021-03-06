# Pabot

A parallel executor for [Robot Framework](http://www.robotframework.org) tests. With Pabot you can split one execution into multiple and save test execution time.

*My goal in creating this tool is to help you guys with big test sets. I've worked with a number of teams around the world that were doing test execution time optimisation before I created this tool. 
I saw similarities in how Robot Framework testing systems have been built and came up with a quite good solution for the basic parallelisation problem. I hope this tool brings you joy and speeds up your test execution! If you are interested in professional support, please contact me through email firstname.lastname(at)gmail.com!* - Mikko Korpela ( those are my firstname and lastname :D )

## Installation:

From PyPi:

     pip install -U robotframework-pabot

OR clone this repository and run:

     setup.py  install

## Command-line options

Supports all Robot Framework command line options and also following options (these must be before normal RF options):

--verbose     
  more output

--command [ACTUAL COMMANDS TO START ROBOT EXECUTOR] --end-command    
  RF script for situations where pybot is not used directly

--processes   [NUMBER OF PROCESSES]          
  How many parallel executors to use (default max of 2 and cpu count)

--pabotlib         
  Start PabotLib remote server. This enables locking and resource distribution between parallel test executions.

--resourcefile [FILEPATH]         
  Indicator for a file that can contain shared variables for distributing resources. This needs to be used together with pabotlib option. Resource file syntax is same as Windows ini files. Where a section is a shared set of variables.

Example usages:

     pabot test_directory
     pabot --exclude FOO directory_to_tests
     pabot --command java -jar robotframework.jar --end-command --include SMOKE tests
     pabot --processes 10 tests

### PabotLib

pabot.PabotLib provides keywords that will help communication and data sharing between the executor processes.
Docs are located at http://htmlpreview.github.io/?https://github.com/mkorpela/pabot/blob/master/PabotLib.html

### PabotLib example:

test.robot

      *** Settings ***
      Library    pabot.PabotLib
      
      *** Test Case ***
      Testing PabotLib
        Acquire Lock   MyLock
        Log   This part is critical section
        Release Lock   MyLock
        ${valuesetname}=    Acquire Value Set
        ${host}=   Get Value From Set   host
        ${username}=     Get Value From Set   username
        ${password}=     Get Value From Set   password
        Log   Do something with the values (for example access host with username and password)
        Release Value Set
        Log   After value set release others can obtain the variable values

valueset.dat

      [Server1]
      HOST=123.123.123.123
      USERNAME=user1
      PASSWORD=password1
      
      [Server2]
      HOST=121.121.121.121
      USERNAME=user2
      PASSWORD=password2
      

pabot call

      pabot --pabotlib --resourcefile valueset.dat test.robot

