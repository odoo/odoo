===================
Profiling Odoo code
===================

.. warning::

    This tutorial requires :ref:`having installed Odoo <setup/install>`
    and :ref:`writing Odoo code <backend>`

Graph a method Up to 10.0
=========================

Odoo embeds a profiler of code. This embeded profiler output can be used to
generate a graph of calls triggered by the method, percentage of time taken in
the method itself as well as time taken in method and it's sub-called methods.

.. code:: python

    from openerp.tools.misc import profile
    [...]
    @profile('/temp/prof.profile')
    @api.multi
    def mymethod(...)

This produce a file called /temp/prof.profile

A tool called *gprof2dot* will produce a graph with this result:

.. code:: bash

    gprof2dot -f pstats -o /temp/prof.xdot /temp/prof.profile

A tool called *xdot* will display the resulting graph:

.. code:: bash
    
    xdot /temp/prof.xdot
    
Dump stack
==========

Sending the SIGQUIT signal to an odoo process (only available on POSIX) makes
this process output the current stack trace to log, with info level. When an
odoo process seems stucked, sending this signal to the process permit to know
what the process is doing, and letting the process continue his job.

Tracing code execution
======================

Instead of sending the SIGQUIT signal to an odoo process often enough, to check
where processes is performing worse than expected, we can use pyflame tool to
do it for us.

Install pyflame and flamegraph
------------------------------

.. code:: bash

    sudo apt install autoconf automake autotools-dev g++ pkg-config python-dev python3-dev libtool make
    git clone https://github.com/uber/pyflame.git
    git clone https://github.com/brendangregg/FlameGraph.git
    cd pyflame
    ./autogen.sh
    ./configure
    make
    sudo make install

Record executed code
--------------------

As pyflame is installed, we now record the executed code lines with pyflame.
This tool will record, multiple times a second, the stacktrace of the process.
Once done, we'll display them as an execution graph.

.. code:: bash

    pyflame --exclude-idle -s 3600 -r 0.2 -p <PID> -o test.flame

where <PID> is the process ID of the odoo process you want to graph. This will
wait until the dead of the process, with a maximum of one hour, and and get 5
traces a second. With the output of pyflame, we can produce an svg graph with
the flamegraph tool:

.. code:: bash

    flamegraph.pl ./test.flame > ~/mycode.svg

.. image:: profile/flamegraph.svg
