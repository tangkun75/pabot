#!/usr/bin/env python

#  Copyright 2014 Nokia Solutions and Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os, sys, time, datetime
import signal
import multiprocessing
from glob import glob
from StringIO import StringIO
import shutil
import subprocess
from robot import run, rebot
from robot.api import ExecutionResult
from robot.result.visitor import ResultVisitor
from multiprocessing.pool import Pool
from tempfile import mkdtemp
from robot.run import USAGE
from robot.utils import ArgumentParser


def execute_and_wait(args):
    datasources, outs_dir, options, suite_name, _, verbose = args
    print 'EXECUTING PARALLEL SUITE %s' % suite_name
    rc = run(*datasources, **_options_for_executor(options, outs_dir, suite_name))
    if rc != 0:
        print 'EXECUTION FAILED IN %s' % suite_name

def execute_and_wait_with(args):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    datasources, outs_dir, options, suite_name, command, verbose = args
    cmd = command + _options_for_custom_executor(options, outs_dir, suite_name) + datasources
    cmd = [c if ' ' not in c else '"%s"' % c for c in cmd]
    if verbose:
        print 'EXECUTING PARALLEL SUITE %s with command:\n%s' % (suite_name, ' '.join(cmd))
    else:
        print 'EXECUTING %s' % suite_name
    process = subprocess.Popen(' '.join(cmd),
                          shell=True,
                          stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE)
    rc = process.wait()
    if rc != 0:
        print _execution_failed_message(suite_name, process, rc, verbose)

def _execution_failed_message(suite_name, process, rc, verbose):
    if not verbose:
        return 'FAILED %s' % suite_name
    msg = ['Execution failed in %s with %d failing test(s)' % (suite_name, rc)]
    stderr = process.stderr.read().strip()
    if stderr:
        msg += ['<< STDERR >>', stderr, '<< END OF STDERR >>']
    return '\n'.join(msg)

def _options_for_executor(options, outs_dir, suite_name):
    options = options.copy()
    options['log'] = 'NONE'
    options['report'] = 'NONE'
    options['suite'] = suite_name
    options['outputdir'] = outs_dir
    options['output'] = '%s.xml' % suite_name
    options['stdout'] = StringIO()
    options['stderr'] = StringIO()
    options['monitorcolors'] = 'off'
    options['monitormarkers'] = 'off'
    return options

def _options_for_custom_executor(*args):
    opts = _options_for_executor(*args)
    res = []
    for k, v in opts.items():
        if isinstance(v, basestring):
            res += ['--' + str(k), str(v)]
        if isinstance(v, bool) and (v is True):
            res += ['--' + str(k)]
        if isinstance(v, list):
            for value in v:
                res += ['--' + str(k), str(value)]
    return res

class GatherSuiteNames(ResultVisitor):

      def __init__(self):
          self.result = []

      def end_suite(self, suite):
          if len(suite.tests):
             self.result.append(suite.longname)

def get_suite_names(output_file):
    if not os.path.isfile(output_file):
       return []
    try:
       e = ExecutionResult(output_file)
       gatherer = GatherSuiteNames()
       e.visit(gatherer)
       return gatherer.result
    except:
       return []

def get_args():
    args = sys.argv[1:]
    pabot_args = {'command':None, 
                  'verbose':False,
                  'processes':max(multiprocessing.cpu_count(), 2)}
    while args and args[0] in ['--command', '--processes', '--verbose']:
        if args[0] == '--command':
            end_index = args.index('--end-command')
            pabot_args['command'] = args[1:end_index]
            args = args[end_index+1:]
        if args[0] == '--processes':
            pabot_args['processes'] = int(args[1])
            args = args[2:]
        if args[0] == '--verbose':
            pabot_args['verbose'] = True
            args = args[1:]
    options, datasources = ArgumentParser(USAGE,
                                          auto_pythonpath=(pabot_args['command'] is None),
                                          auto_argumentfile=(pabot_args['command'] is None)).parse_args(args)
    keys = set()
    for k in options:
        if options[k] is None:
            keys.add(k)
    for k in keys:
        del options[k]
    return options, datasources, pabot_args

def solve_suite_names(outs_dir, datasources, options):
    options = options.copy()
    options['log'] = 'NONE'
    options['report'] = 'NONE'
    options['dryrun'] = True
    options['output'] = 'suite_names.xml'
    options['outputdir'] = outs_dir
    options['stdout'] = StringIO()
    options['stderr'] = StringIO()
    options['monitorcolors'] = 'off'
    options['monitormarkers'] = 'off'
    run(*datasources, **options)
    output = os.path.join(outs_dir, 'suite_names.xml')
    suite_names = get_suite_names(output)
    if os.path.isfile(output):
        os.remove(output)
    return suite_names

def _options_for_rebot(options, datasources, start_time_string, end_time_string):
    rebot_options = options.copy()
    rebot_options['name'] = ', '.join(datasources)
    rebot_options['starttime'] = start_time_string
    rebot_options['endtime'] = end_time_string
    return rebot_options

def _now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

def _print_elapsed(start, end):
    elapsed = end - start
    millis = int((elapsed * 1000) % 1000)
    seconds = int(elapsed) % 60
    elapsed_minutes = (int(elapsed)-seconds)/60
    minutes = elapsed_minutes % 60
    elapsed_hours = (elapsed_minutes-minutes)/60
    elapsed_string = ''
    if elapsed_hours > 0:
        elapsed_string += '%d hours ' % elapsed_hours
    elapsed_string += '%d minutes %d.%d seconds' % (minutes, seconds, millis) 
    print 'Elapsed time: '+elapsed_string


if __name__ == '__main__':
    start_time = time.time()
    start_time_string = _now()
    outs_dir = mkdtemp()
    try:
        options, datasources, pabot_args = get_args()
        suite_names = solve_suite_names(outs_dir, datasources, options)
        if suite_names:
            process_pool = Pool(pabot_args['processes'])
            process_pool.map_async(execute_and_wait if not pabot_args['command'] else execute_and_wait_with,
                                   [(datasources, outs_dir, options, suite, pabot_args['command'], pabot_args['verbose']) for suite in suite_names])
            process_pool.close()
            process_pool.join()
        end_time_string = _now()
        sys.exit(rebot(*sorted(glob(os.path.join(outs_dir, '*.xml'))), **_options_for_rebot(options, datasources, start_time_string, end_time_string)))
    finally:
        shutil.rmtree(outs_dir)
        _print_elapsed(start_time, time.time())


