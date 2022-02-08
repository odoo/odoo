Javascript Finite State Machine (v2.1.0)
========================================

This standalone javascript micro-framework provides a finite state machine for your pleasure.

 * You can find the [code here](https://github.com/jakesgordon/javascript-state-machine)
 * You can find a [description here](http://codeincomplete.com/posts/2011/8/19/javascript_state_machine_v2/)
 * You can find a [working demo here](http://codeincomplete.com/posts/2011/8/19/javascript_state_machine_v2/example/)

Download
========

You can download [state-machine.js](https://github.com/jakesgordon/javascript-state-machine/raw/master/state-machine.js),
or the [minified version](https://github.com/jakesgordon/javascript-state-machine/raw/master/state-machine.min.js)

Alternatively:

    git clone git@github.com:jakesgordon/javascript-state-machine


 * All code is in state-machine.js
 * Minified version provided in state-machine.min.js
 * No 3rd party library is required
 * Demo can be found in /index.html
 * QUnit tests can be found in /test/index.html

Usage
=====

Include `state-machine.min.js` in your application.

In its simplest form, create a standalone state machine using:

    var fsm = StateMachine.create({
      initial: 'green',
      events: [
        { name: 'warn',  from: 'green',  to: 'yellow' },
        { name: 'panic', from: 'yellow', to: 'red'    },
        { name: 'calm',  from: 'red',    to: 'yellow' },
        { name: 'clear', from: 'yellow', to: 'green'  }
    ]});

... will create an object with a method for each event:

 * fsm.warn()  - transition from 'green' to 'yellow'
 * fsm.panic() - transition from 'yellow' to 'red'
 * fsm.calm()  - transition from 'red' to 'yellow'
 * fsm.clear() - transition from 'yellow' to 'green'

along with the following members:

 * fsm.current   - contains the current state
 * fsm.is(s)     - return true if state `s` is the current state
 * fsm.can(e)    - return true if event `e` can be fired in the current state
 * fsm.cannot(e) - return true if event `e` cannot be fired in the current state

Multiple 'from' and 'to' states for a single event
==================================================

If an event is allowed **from** multiple states, and always transitions to the same
state, then simply provide an array of states in the `from` attribute of an event. However,
if an event is allowed from multiple states, but should transition **to** a different
state depending on the current state, then provide multiple event entries with
the same name:

    var fsm = StateMachine.create({
      initial: 'hungry',
      events: [
        { name: 'eat',  from: 'hungry',                                to: 'satisfied' },
        { name: 'eat',  from: 'satisfied',                             to: 'full'      },
        { name: 'eat',  from: 'full',                                  to: 'sick'      },
        { name: 'rest', from: ['hungry', 'satisfied', 'full', 'sick'], to: 'hungry'    },
    ]});

This example will create an object with 2 event methods:

 * fsm.eat()
 * fsm.rest()

The `rest` event will always transition to the `hungry` state, while the `eat` event
will transition to a state that is dependent on the current state.

>> NOTE: The `rest` event could use a wildcard '*' for the 'from' state if it should be
allowed from any current state.

>> NOTE: The `rest` event in the above example can also be specified as multiple events with
the same name if you prefer the verbose approach.

Callbacks
=========

4 callbacks are available if your state machine has methods using the following naming conventions:

 * onbefore**event** - fired before the event
 * onleave**state**  - fired when leaving the old state
 * onenter**state**  - fired when entering the new state
 * onafter**event**  - fired after the event

You can affect the event in 3 ways:

 * return `false` from an `onbeforeevent` handler to cancel the event.
 * return `false` from an `onleavestate` handler to cancel the event.
 * return `ASYNC` from an `onleavestate` handler to perform an asynchronous state transition (see next section)

For convenience, the 2 most useful callbacks can be shortened:

 * on**event** - convenience shorthand for onafter**event**
 * on**state** - convenience shorthand for onenter**state**

In addition, a generic `onchangestate()` callback can be used to call a single function for _all_ state changes:

All callbacks will be passed the same arguments:

 * **event** name
 * **from** state
 * **to** state
 * _(followed by any arguments you passed into the original event method)_

Callbacks can be specified when the state machine is first created:

    var fsm = StateMachine.create({
      initial: 'green',
      events: [
        { name: 'warn',  from: 'green',  to: 'yellow' },
        { name: 'panic', from: 'yellow', to: 'red'    },
        { name: 'calm',  from: 'red',    to: 'yellow' },
        { name: 'clear', from: 'yellow', to: 'green'  }
      ],
      callbacks: {
        onpanic:  function(event, from, to, msg) { alert('panic! ' + msg);               },
        onclear:  function(event, from, to, msg) { alert('thanks to ' + msg);            },
        ongreen:  function(event, from, to)      { document.body.className = 'green';    },
        onyellow: function(event, from, to)      { document.body.className = 'yellow';   },
        onred:    function(event, from, to)      { document.body.className = 'red';      },
      }
    });

    fsm.panic('killer bees');
    fsm.clear('sedatives in the honey pots');
    ...

Additionally, they can be added and removed from the state machine at any time:

    fsm.ongreen       = null;
    fsm.onyellow      = null;
    fsm.onred         = null;
    fsm.onchangestate = function(event, from, to) { document.body.className = to; };

Asynchronous State Transitions
==============================

Sometimes, you need to execute some asynchronous code during a state transition and ensure the
new state is not entered until your code has completed.

A good example of this is when you transition out of a `menu` state, perhaps you want to gradually
fade the menu away, or slide it off the screen and don't want to transition to your `game` state
until after that animation has been performed.

You can now return `StateMachine.ASYNC` from your `onleavestate` handler and the state machine
will be _'put on hold'_ until you are ready to trigger the transition using the new `transition()`
method.

For example, using jQuery effects:

    var fsm = StateMachine.create({

      initial: 'menu',

      events: [
        { name: 'play', from: 'menu', to: 'game' },
        { name: 'quit', from: 'game', to: 'menu' }
      ],

      callbacks: {

        onentermenu: function() { $('#menu').show(); },
        onentergame: function() { $('#game').show(); },

        onleavemenu: function() {
          $('#menu').fadeOut('fast', function() {
            fsm.transition();
          });
          return StateMachine.ASYNC; // tell StateMachine to defer next state until we call transition (in fadeOut callback above)
        },

        onleavegame: function() {
          $('#game').slideDown('slow', function() {
            fsm.transition();
          };
          return StateMachine.ASYNC; // tell StateMachine to defer next state until we call transition (in slideDown callback above)
        }

      }
    });


State Machine Classes
=====================

You can also turn all instances of a  _class_ into an FSM by applying
the state machine functionality to the prototype, including your callbacks
in your prototype, and providing a `startup` event for use when constructing
instances:

    MyFSM = function() {    // my constructor function
      this.startup();
    };

    MyFSM.prototype = {

      onpanic: function(event, from, to) { alert('panic');        },
      onclear: function(event, from, to) { alert('all is clear'); },

      // my other prototype methods

    };

    StateMachine.create({
      target: MyFSM.prototype,
      events: [
        { name: 'startup', from: 'none',   to: 'green'  },
        { name: 'warn',    from: 'green',  to: 'yellow' },
        { name: 'panic',   from: 'yellow', to: 'red'    },
        { name: 'calm',    from: 'red',    to: 'yellow' },
        { name: 'clear',   from: 'yellow', to: 'green'  }
      ]});


This should be easy to adjust to fit your appropriate mechanism for object construction.

Initialization Options
======================

How the state machine should initialize can depend on your application requirements, so
the library provides a number of simple options.

By default, if you dont specify any initial state, the state machine will be in the `'none'`
state and you would need to provide an event to take it out of this state:

    var fsm = StateMachine.create({
      events: [
        { name: 'startup', from: 'none',  to: 'green' },
        { name: 'panic',   from: 'green', to: 'red'   },
        { name: 'calm',    from: 'red',   to: 'green' },
    ]});
    alert(fsm.current); // "none"
    fsm.startup();
    alert(fsm.current); // "green"

If you specify the name of your initial event (as in all the earlier examples), then an
implicit `startup` event will be created for you and fired when the state machine is constructed.

    var fsm = StateMachine.create({
      initial: 'green',
      events: [
        { name: 'panic', from: 'green', to: 'red'   },
        { name: 'calm',  from: 'red',   to: 'green' },
    ]});
    alert(fsm.current); // "green"

If your object already has a `startup` method you can use a different name for the initial event

    var fsm = StateMachine.create({
      initial: { state: 'green', event: 'init' },
      events: [
        { name: 'panic', from: 'green', to: 'red'   },
        { name: 'calm',  from: 'red',   to: 'green' },
    ]});
    alert(fsm.current); // "green"

Finally, if you want to wait to call the initial state transition event until a later date you
can `defer` it:

    var fsm = StateMachine.create({
      initial: { state: 'green', event: 'init', defer: true },
      events: [
        { name: 'panic', from: 'green', to: 'red'   },
        { name: 'calm',  from: 'red',   to: 'green' },
    ]});
    alert(fsm.current); // "none"
    fsm.init();
    alert(fsm.current); // "green"

Of course, we have now come full circle, this last example is pretty much functionally the
same as the first example in this section where you simply define your own startup event.

So you have a number of choices available to you when initializing your state machine.

Handling Failures
======================

By default, if you try to call an event method that is not allowed in the current state, the
state machine will throw an exception. If you prefer to handle the problem yourself, you can
define a custom `error` handler:

    var fsm = StateMachine.create({
      initial: 'green',
      error: function(eventName, from, to, args, errorCode, errorMessage) {
        return 'event ' + eventName + ' was naughty :- ' + errorMessage;
      },
      events: [
        { name: 'panic', from: 'green', to: 'red'   },
        { name: 'calm',  from: 'red',   to: 'green' },
    ]});
    alert(fsm.calm()); // "event calm was naughty :- event not allowed in current state green"

Release Notes
=============

See [RELEASE NOTES](https://github.com/jakesgordon/javascript-state-machine/blob/master/RELEASE_NOTES.md) file.

License
=======

See [LICENSE](https://github.com/jakesgordon/javascript-state-machine/blob/master/LICENSE) file.

Contact
=======

If you have any ideas, feedback, requests or bug reports, you can reach me at
[jake@codeincomplete.com](mailto:jake@codeincomplete.com), or via
my website: [Code inComplete](http://codeincomplete.com/posts/2011/8/19/javascript_state_machine_v2/)





