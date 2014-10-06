Select2
=======

Select2 is a jQuery-based replacement for select boxes. It supports searching, remote data sets, and infinite scrolling of results.

To get started, checkout examples and documentation at http://ivaynberg.github.com/select2

Use cases
---------

* Enhancing native selects with search.
* Enhancing native selects with a better multi-select interface.
* Loading data from JavaScript: easily load items via ajax and have them searchable.
* Nesting optgroups: native selects only support one level of nested. Select2 does not have this restriction.
* Tagging: ability to add new items on the fly.
* Working with large, remote datasets: ability to partially load a dataset based on the search term.
* Paging of large datasets: easy support for loading more pages when the results are scrolled to the end.
* Templating: support for custom rendering of results and selections.

Browser compatibility
---------------------
* IE 8+
* Chrome 8+
* Firefox 10+
* Safari 3+
* Opera 10.6+
 
Usage
-----
You can source Select2 directly from a [CDN like JSDliver](http://www.jsdelivr.com/#!select2), [download it from this GitHub repo](https://github.com/ivaynberg/select2/tags), or use one of the integrations below.

Integrations
------------

* [Wicket-Select2](https://github.com/ivaynberg/wicket-select2) (Java / [Apache Wicket](http://wicket.apache.org))
* [select2-rails](https://github.com/argerim/select2-rails) (Ruby on Rails)
* [AngularUI](http://angular-ui.github.com/#directives-select2) ([AngularJS](angularjs.org))
* [Django](https://github.com/applegrew/django-select2)
* [Symfony](https://github.com/19Gerhard85/sfSelect2WidgetsPlugin)
* [Symfony2](https://github.com/avocode/FormExtensions)
* [Bootstrap 2](https://github.com/t0m/select2-bootstrap-css) and [Bootstrap 3](https://github.com/t0m/select2-bootstrap-css/tree/bootstrap3) (CSS skins)
* [Meteor](https://github.com/nate-strauser/meteor-select2) (modern reactive JavaScript framework; + [Bootstrap 3 skin](https://github.com/esperadomedia/meteor-select2-bootstrap3-css/))
* [Meteor](https://jquery-select2.meteor.com)
* [Yii 2.x](http://demos.krajee.com/widgets#select2)
* [Yii 1.x](https://github.com/tonybolzan/yii-select2)
* [AtmosphereJS](https://atmospherejs.com/package/jquery-select2)

### Example Integrations

* [Knockout.js](https://github.com/ivaynberg/select2/wiki/Knockout.js-Integration)
* [Socket.IO](https://github.com/ivaynberg/select2/wiki/Socket.IO-Integration)
* [PHP](https://github.com/ivaynberg/select2/wiki/PHP-Example)
* [.Net MVC] (https://github.com/ivaynberg/select2/wiki/.Net-MVC-Example)

Internationalization (i18n)
---------------------------

Select2 supports multiple languages by simply including the right language JS
file (`select2_locale_it.js`, `select2_locale_nl.js`, etc.) after `select2.js`.

Missing a language? Just copy `select2_locale_en.js.template`, translate
it, and make a pull request back to Select2 here on GitHub.

Bug tracker
-----------

Have a bug? Please create an issue here on GitHub!

https://github.com/ivaynberg/select2/issues

Mailing list
------------

Have a question? Ask on our mailing list!

select2@googlegroups.com

https://groups.google.com/d/forum/select2


Copyright and license
---------------------

Copyright 2012 Igor Vaynberg

This software is licensed under the Apache License, Version 2.0 (the "Apache License") or the GNU
General Public License version 2 (the "GPL License"). You may choose either license to govern your
use of this software only upon the condition that you accept all of the terms of either the Apache
License or the GPL License.

You may obtain a copy of the Apache License and the GPL License in the LICENSE file, or at:

http://www.apache.org/licenses/LICENSE-2.0
http://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the Apache License
or the GPL License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the Apache License and the GPL License for the specific language governing
permissions and limitations under the Apache License and the GPL License.
