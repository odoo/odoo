Gamification module documentation
=================================

The Gamification module holds all the module and logic related to goals, plans and badges. The computation is mainly done in this module, other modules inherating from it should only add data and tests.

Goals
-----
A **Goal** is an objective applied to an user with a numerical target to reach. It can have a starting and end date. Users usually do not create goals but relies on goal plans.

A **Goal Type** is a generic objective that can be applied to any structure stored in the database and use numerical value. The creation of goal types is quite technical and should rarely be done. Once a generic goal is created, it can be associated to several goal plans with different numerical targets.

A **Goal Plan** is a a set of goal types with a target value to reach applied to a group of users. It can be periodic to create and evaluate easily the performances of a team.

Badges
------
A **Badge** is a symbolic token granted to a user as a sign of reward. It can be offered by a user to another or automatically offered when some conditions are met. The conditions can either be a list of goal types succeeded or a user definied python code executed.

