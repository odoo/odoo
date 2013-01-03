Select2
=================

Select2 is a jQuery based replacement for select boxes. It supports searching, remote data sets, and infinite scrolling of results. Look and feel of Select2 is based on the excellent [Chosen](http://harvesthq.github.com/chosen/) library.

To get started -- checkout http://ivaynberg.github.com/select2!

What Does Select2 Support That Chosen Does Not?
-------------------------------------------------

* Working with large datasets: Chosen requires the entire dataset to be loaded as `option` tags in the DOM, which limits
it to working with small-ish datasets. Select2 uses a function to find results on-the-fly, which allows it to partially
load results.
* Paging of results: Since Select2 works with large datasets and only loads a small amount of matching results at a time
it has to support paging. Select2 will call the search function when the user scrolls to the bottom of currently loaded
result set allowing for the 'infinite scrolling' of results.
* Custom markup for results: Chosen only supports rendering text results because that is the only markup supported by
`option` tags. Select2 provides an extension point which can be used to produce any kind of markup to represent results.
* Ability to add results on the fly: Select2 provides the ability to add results from the search term entered by the user, which allows it to be used for
tagging.

Browser Compatibility
--------------------
* IE 8+ (7 mostly works except for [issue with z-index](https://github.com/ivaynberg/select2/issues/37))
* Chrome 8+
* Firefox 3.5+
* Safari 3+
* Opera 10.6+

Integrations
------------

* [Wicket-Select2](https://github.com/ivaynberg/wicket-select2) (Java / Apache Wicket)
* [select2-rails](https://github.com/argerim/select2-rails) (Ruby on Rails)
* [AngularUI](http://angular-ui.github.com/#directives-select2) ([AngularJS](angularjs.org))
* [Django](https://github.com/applegrew/django-select2)

Bug tracker
-----------

Have a bug? Please create an issue here on GitHub!

https://github.com/ivaynberg/select2/issues


Mailing list
------------

Have a question? Ask on our mailing list!

select2@googlegroups.com

https://groups.google.com/d/forum/select2


Copyright and License
---------------------

Copyright 2012 Igor Vaynberg

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this work except in
compliance with the License. You may obtain a copy of the License in the LICENSE file, or at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.