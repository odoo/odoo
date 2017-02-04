---
layout: default
title: Select2 4.0.0 Released
slug: announcements-4.0
---
<section id="pre-release" class="jumbotron">
  <div class="container">
    <h1>Announcing Select2 4.0.0</h1>
  </div>
</section>

<div class="container s2-docs-container">
  <div class="row">
    <div class="col-md-9" role="main">

      <section id="release">
        <h1 class="page-header">Select2 4.0.0</h1>

        <p class="lead">
          The 4.0 release of Select2 is the result of three years of working on the
          code base and watching where it needs to go. At the core, it is a full
          rewrite that addresses many of the extensibility and usability problems
          that could not be addressed in previous versions.
        </p>

        <p>
          This release contains many breaking changes, but easy-upgrade paths have
          been created as well as helper modules that will allow for backwards
          compatibility to be maintained with past versions of Select2. Upgrading
          <em>will</em> require you to read the release notes carefully, but the
          migration path should be relatively straightforward. You can view a list
          of the most common changes that you will need to make
          <a href="https://github.com/select2/select2/releases">in the release notes</a>.
        </p>

        <p>
          Below is an in-depth review of what is new in Select2, as well as some of
          the major changes that have been made.
        </p>
      </section>

      <section id="new">
        <h2>New features</h2>

        <p>
          The notable features of this new release include:
        </p>

        <ul>
          <li>
            A more flexible plugin framework that allows you to override Select2 to
            behave exactly how you want it to.
          </li>
          <li>
            Consistency with standard <code>&lt;select&gt;</code> elements for all
            data adapters, removing the need for hidden <code>&lt;input&gt;</code>
            elements.
          </li>
          <li>
            A new build system that uses AMD to keep everything organized.
          </li>
          <li>
            Less specific selectors allowing for Select2 to be styled to fit the
            rest of your application.
          </li>
        </ul>
      </section>

      <section id="plugins">
        <h2>Plugin system</h2>

        <p>
          Select2 now provides interfaces that allow for it to be easily extended,
          allowing for anyone to create a plugin that changes the way Select2 works.
          This is the result of Select2 being broken into four distinct sections,
          each of which can be extended and used together to create your unique
          Select2.
        </p>

        <p>
          The adapters implement a consistent interface that is documented in the
          <a href="options.html#adapters">options section for adapters</a>, allowing
          you to customize Select2 to do exactly what you are looking for. Select2
          is designed such that you can mix and match plugins, with most of the core
          options being built as decorators that wrap the standard adapters.
        </p>
      </section>

      <section id="amd-builds">
        <h2>AMD-based build system</h2>

        <p>
          Select2 now uses an
          <a href="https://en.wikipedia.org/wiki/Asynchronous_module_definition">AMD-based build system</a>,
          allowing for builds that only require the parts of Select2 that you need.
          While a custom build system has not yet been created, Select2 is open
          source and will gladly accept a pull request for one.
        </p>

        <p>
          Select2 includes the minimal <a href="https://github.com/jrburke/almond">almond</a>
          AMD loader, but a custom <code>select2.amd.js</code> build is available
          if you already use an AMD loader. The code base (available in the
          <code>src</code> directory) also uses AMD, allowing you to include Select2
          in your own build system and generate your own builds alongside your
          existing infrastructure.
        </p>

        <p>
          The AMD methods used by Select2 are available as
          <code>jQuery.fn.select2.amd.define()/require()</code>, allowing you to use the
          included almond loader. These methods are primarily used by the
          translations, but they are the recommended way to access custom modules
          that Select2 provides.
        </p>
      </section>

      <section id="migrating">
        <h1>Migrating from Select2 3.5</h1>

        <p>
          There are a few breaking changes that migrators should be aware of when
          they are coming from older versions of Select2.
        </p>

        <p>
          If you use the full build of Select2 (<code>select2.full.js</code>), you
          will be automatically notified of the major breaking changes, and
          compatibility modules will be used in some cases to ensure that your code
          still behaves how you were expecting.
        </p>

        <h2 id="hidden-input">No more hidden input tags</h2>

        <p>
          In past versions of Select2, an <code>&lt;input type="hidden" /&gt;</code>
          tag was recommended if you wanted to do anything advanced with Select2,
          such as work with remote data sources or allow users to add their own
          tags. This had the unfortunate side-effect of servers not receiving the
          data from Select2 as an array, like a standard <code>&lt;select&gt;</code>
          element does, but instead sending a string containing the comma-separated
          strings. The code base ended up being littered with special cases for the
          hidden input, and libraries using Select2 had to work around the
          differences it caused.
        </p>

        <p>
          In Select2 4.0, the <code>&lt;select&gt;</code> element supports all core
          options, and support for the old
          <code>&lt;input type="hidden" /&gt;</code> has been deprecated. This means
          that if you previously declared an AJAX field with some pre-selected
          options that looked like…
        </p>

{% highlight html linenos %}
<input type="hidden" name="select-boxes" value="1,2,4,6" />
{% endhighlight %}

        <p>
          It will need to be recreated as a <code>&lt;select&gt;</code> element with
          some <code>&lt;option&gt;</code> tags that have <code>value</code>
          attributes that match the old value.
        </p>

{% highlight html linenos %}
<select name="select-boxes" multiple="multiple">
  <option value="1" selected="selected">Select2</option>
  <option value="2" selected="selected">Chosen</option>
  <option value="4" selected="selected">selectize.js</option>
  <option value="6" selected="selected">typeahead.js</option>
</select>
{% endhighlight %}

        <p>
          The options that you create should have <code>selected="selected"</code>
          set so Select2 and the browser knows that they should be selected. The
          <code>value</code> attribute of the option should also be set to the value
          that will be returned from the server for the result, so Select2 can
          highlight it as selected in the dropdown. The text within the option
          should also reflect the value that should be displayed by default for the
          option.
        </p>

        <h2 id="new-matcher">Advanced matching of searches</h2>

        <p>
          In past versions of Select2, when matching search terms to individual
          options, which limited the control that you had when displaying results,
          especially in cases where there was nested data. The <code>matcher</code>
          function was only given the individual option, even if it was a nested
          options, without any context.
        </p>

        <p>
          With the new matcher function, only the root-level options are matched and
          matchers are expected to limit the results of any children options that
          they contain. This allows developers to customize how options within
          groups can be displayed, and modify how the results are returned.
        </p>

        <p>
          A function has been created that allows old-style matcher functions to be
          converted to the new style. You can retrieve the function from the
          <code>select2/compat/matcher</code> module, which should just wrap the old
          matcher function.
        </p>

        <p>
          So if your old code used a matcher that only displayed options if they
          started with the term that was entered, it would look something like…
        </p>

{% highlight js linenos %}
function matchStart (term, text) {
  if (text.toUpperCase().indexOf(term.toUpperCase()) == 0) {
    return true;
  }

  return false;
}

$("select").select2({
  matcher: matchStart
})
{% endhighlight %}

        <p>
          Then in Select2 4.0, you would need to wrap the <code>matchStart</code>
          method (or the name of the matcher you created) with a
          <code>oldMatcher</code> method that we have created.
        </p>

{% highlight js linenos %}
function matchStart (term, text) {
  if (text.toUpperCase().indexOf(term.toUpperCase()) == 0) {
    return true;
  }

  return false;
}

$.fn.select2.amd.require(['select2/compat/matcher'], function (oldMatcher) {
  $("select").select2({
    matcher: oldMatcher(matchStart)
  })
});
{% endhighlight %}

        <p>
          This will work for any matchers that only took in the search term and the
          text of the option as parameters. If your matcher relied on the third
          parameter containing the jQuery element representing the original
          <code>&lt;option&gt;</code> tag, then you may need to slightly change
          your matcher to expect the full JavaScript data object being passed in
          instead. You can still retrieve the jQuery element from the data object
          using the <code>data.element</code> property.
        </p>

        <h2 id="flexible-placeholders">More flexible placeholders</h2>

        <p>
          In the most recent versions of Select2, placeholders could only be
          applied to the first (typically the default) option in a
          <code>&lt;select&gt;</code> if it was blank. The
          <code>placeholderOption</code> option was added to Select2 to allow users
          using the <code>select</code> tag to select a different option, typically
          an automatically generated option with a different value.
        </p>

        <p>
          The <code>placeholder</code> option can now take an object as well as just
          a string. This replaces the need for the old
          <code>placeholderOption</code>, as now the <code>id</code> of the object
          can be set to the <code>value</code> attribute of the
          <code>&lt;option&gt;</code> tag.
        </p>

        <p>
          For a select that looks like the following, where the first option (with a
          value of <code>-1</code>) is the placeholder option…
        </p>

{% highlight html linenos %}
<select>
  <option value="-1" selected="selected">Select an option</option>
  <option value="1">Something else</option>
</select>
{% endhighlight %}

        <p>
          You would have previously had to get the placeholder option through the
          <code>placeholderOption</code>, but now you can do it through the
          <code>placeholder</code> option by setting an <code>id</code>.
        </p>

{% highlight js linenos %}
$("select").select2({
  placeholder: {
    id: "-1",
    placeholder: "Select an option"
  }
})
{% endhighlight %}

        <p>
          And Select2 will automatically display the placeholder when the value of
          the select is <code>-1</code>, which it will be by default. This does not
          break the old functionality of Select2 where the placeholder option was
          blank by default.
        </p>

        <h2 id="value-ordering">Display reflects the actual order of the values</h2>

        <p>
          In past versions of Select2, choices were displayed in the order that
          they were selected. In cases where Select2 was used on a
          <code>&lt;select&gt;</code> element, the order that the server received
          the selections did not always match the order that the choices were
          displayed, resulting in confusion in situations where the order is
          important.
        </p>

        <p>
          Select2 will now order selected choices in the same order that will be
          sent to the server.
        </p>

        <h2 id="changed-options">Changed method and option names</h2>

        <p>
          When designing the future option set for Select2 4.0, special care was
          taken to ensure that the most commonly used options were brought over.
          For the most part, the commonly used options of Select2 can still be
          referenced under their previous names, but there were some changes which
          have been noted.
        </p>

        <h3 id="removed-initselection">
          Removed the requirement of <code>initSelection</code>
        </h3>

        <p>
          In the past, whenever you wanted to use a custom data adapter, such as
          AJAX or tagging, you needed to help Select2 out in determining the initial
          values that were selected. This was typically done through the
          <code>initSelection</code> option, which took the underlying data of the
          input and converted it into data objects that Select2 could use.
        </p>

        <p>
          This is now handled by
          <a href="options.html#dataAdapter">the data adapter</a> in the
          <code>current</code> method, which allows Select2 to convert the currently
          selected values into data objects that can be displayed. The default
          implementation converts the text and value of <code>option</code> elements
          into data objects, and is probably suitable for most cases. An example of
          the old <code>initSelection</code> option is included below, which
          converts the value of the selected options into a data object with both
          the <code>id</code> and <code>text</code> matching the selected value.
        </p>

{% highlight js linenos %}
{
  initSelection : function (element, callback) {
    var data = [];
    $(element.val()).each(function () {
      data.push({id: this, text: this});
    });
    callback(data);
  }
}
{% endhighlight %}

        <p>
          When using the new <code>current</code> method of the custom data adapter,
          <strong>this method is called any time Select2 needs a list</strong> of
          the currently selected options. This is different from the old
          <code>initSelection</code> in that it was only called once, so it could
          suffer from being relatively slow to process the data (such as from a
          remote data source).
        </p>

{% highlight js linenos %}
$.fn.select2.amd.require([
  'select2/data/array',
  'select2/utils'
], function (ArrayData, Utils) {
  function CustomData ($element, options) {
    CustomData.__super__.constructor.call(this, $element, options);
  }

  Utils.Extend(CustomData, ArrayData);

  CustomData.prototype.current = function (callback) {
    var data = [];
    var currentVal = this.$element.val();

    if (!this.$element.prop('multiple')) {
      currentVal = [currentVal];
    }

    for (var v = 0; v < currentVal.length; v++) {
      data.push({
        id: currentVal[v],
        text: currentVal[v]
      });
    }

    callback(data);
  };

  $("#select").select2({
    dataAdapter: CustomData
  });
}
{% endhighlight %}

        <p>
          The new <code>current</code> method of the data adapter works in a similar
          way to the old <code>initSelection</code> method, with three notable
          differences. The first, and most important, is that <strong>it is called
          whenever the current selections are needed</strong> to ensure that Select2
          is always displaying the most accurate and up to date data. No matter
          what type of element Select2 is attached to, whether it supports a
          single or multiple selections, the data passed to the callback
          <strong>must be an array, even if it contains one selection</strong>.
          The last is that there is only one parameter, the callback to be
          executed with the latest data, and the current element that Select2 is
          attached to is available on the class itself as
          <code>this.$element</code>.
        </p>

        <p>
          If you only need to load in the initial options once, and otherwise will
          be letting Select2 handle the state of the selections, you don't need to
          use a custom data adapter. You can just create the
          <code>&lt;option&gt;</code> tags on your own, and Select2 will pick up
          the changes.
        </p>

{% highlight js linenos %}
var $element = $('select').select2(); // the select element you are working with

var $request = $.ajax({
  url: '/my/remote/source' // wherever your data is actually coming from
});

$request.then(function (data) {
  // This assumes that the data comes back as an array of data objects
  // The idea is that you are using the same callback as the old `initSelection`

  for (var d = 0; d < data.length; d++) {
    var item = data[d];

    // Create the DOM option that is pre-selected by default
    var option = new Option(item.text, item.id, true, true);

    // Append it to the select
    $element.append(option);
  }

  // Update the selected options that are displayed
  $element.trigger('change');
});
{% endhighlight %}

        <h3 id="query-to-data-adapter">
          Custom data adapters instead of <code>query</code>
        </h3>

        <p>
          <a href="http://select2.github.io/select2/#data">In the past</a>, any time
          you wanted to hook Select2 up to a different data source you would be
          required to implement custom <code>query</code> and
          <code>initSelection</code> methods. This allowed Select2 to determine the
          initial selection and the list of results to display, and it would handle
          everything else internally, which was fine more most people.
        </p>

        <p>
          The custom <code>query</code> and <code>initSelection</code> methods have
          been replaced by
          <a href="options.html#dataAdapter">custom data adapters</a> that handle
          how Select2 stores and retrieves the data that will be displayed to the
          user. An example of the old <code>query</code> option is provided below,
          which is
          <a href="http://select2.github.io/select2/#data">the same as the old example</a>,
          and it generates results that contain the search term repeated a certain
          number of times.
        </p>

{% highlight js linenos %}
{
  query: function (query) {
    var data = {results: []}, i, j, s;
    for (i = 1; i < 5; i++) {
      s = "";
      for (j = 0; j < i; j++) {s = s + query.term;}
      data.results.push({id: query.term + i, text: s});
    }
    query.callback(data);
  }
}
{% endhighlight %}

        <p>
          This has been replaced by custom data adapters which define a similarly
          named <code>query</code> method. The comparable data adapter is provided
          below as an example.
        </p>

{% highlight js linenos %}
$.fn.select2.amd.require([
  'select2/data/array',
  'select2/utils'
], function (ArrayData, Utils) {
  function CustomData ($element, options) {
    CustomData.__super__.constructor.call(this, $element, options);
  }

  Utils.Extend(CustomData, ArrayData);

  CustomData.prototype.query = function (params, callback) {
    var data = {
      results: []
    };

    for (var i = 1; i < 5; i++) {
      var s = "";

      for (var j = 0; j < i; j++) {
        s = s + params.term;
      }

      data.results.push({
        id: params.term + i,
        text: s
      });
    }

    callback(data);
  };

  $("#select").select2({
    dataAdapter: CustomData
  });
}
{% endhighlight %}

        <p>
          The new <code>query</code> method of the data adapter is very similar to
          the old <code>query</code> option that was passed into Select2 when
          initializing it. The old <code>query</code> argument is mostly the same as
          the new <code>params</code> that are passed in to query on, and the
          callback that should be used to return the results is now passed in as the
          second parameter.
        </p>

        <h3 id="changed-templating">Renamed templating options</h3>

        <p>
          Select2 previously provided multiple options for formatting the results
          list and selected options, commonly referred to as "formatters", using the
          <code>formatSelection</code> and <code>formatResult</code> options. As the
          "formatters" were also used for things such as localization,
          <a href="#changed-translations">which has also changed</a>, they have been
          renamed to <code>templateSelection</code> and <code>templateResult</code>
          and their signatures have changed as well.
        </p>

        <p>
          You should refer to the updated
          <a href="options.html#templating">documentation on templates</a> when
          migrating from previous versions of Select2.
        </p>

        <h3 id="changed-id">
          The <code>id</code> and <code>text</code> properties are strictly enforced
        </h3>

        <p>
          When working with array and AJAX data in the past, Select2 allowed a
          custom <code>id</code> function or attribute to be set in various places,
          ranging from the initialization of Select2 to when the remote data was
          being returned. This allowed Select2 to better integrate with existing
          data sources that did not necessarily use the <code>id</code> attribute to
          indicate the unique identifier for an object.
        </p>

        <p>
          Select2 no longer supports a custom <code>id</code> or <code>text</code>
          to be used, but provides integration points for converting incorrect data
          to the expected format.
        </p>

        <h4>
          When working with array data
        </h4>

        <p>
          Select2 previously supported defining array data as an object that matched
          the signature of an AJAX response. A <code>text</code> property could be
          specified that would map the given property to the <code>text</code>
          property on the individual objects. You can now do this when initializing
          Select2 by using the following jQuery code to map the old
          <code>text</code> and <code>id</code> properties to the new ones.
        </p>

{% highlight js linenos %}
var data = $.map([
  {
    pk: 1,
    word: 'one'
  },
  {
    pk: 2,
    word: 'two'
  }
], function (obj) {
  obj.id = obj.id || obj.pk;
  obj.text = obj.text || obj.word;

  return obj;
});
{% endhighlight %}

        <p>
          This will result in an array of data objects that have the <code>id</code>
          properties that match the existing <code>pk</code> properties and
          <code>text</code> properties that match the existing <code>word</code>
          properties.
        </p>

        <h4>
          When working with remote data
        </h4>

        <p>
          The same code that was given above can be used in the
          <code>processResults</code> method of an AJAX call to map properties there
          as well.
        </p>

        <h3 id="changed-translations">Renamed translation options</h3>

        <p>
          In previous versions of Select2, the default messages provided to users
          could be localized to fit the language of the website that it was being
          used on. Select2 only comes with the English language by default, but
          provides
          <a href="options.html#language">community-contributed translations</a> for
          many common languages. Many of the formatters have been moved to the
          <code>language</code> option and the signatures of the formatters have
          been changed to handle future additions.
        </p>

        <h3 id="changed-data">
          Declaring options using <code>data-*</code> attributes
        </h3>

        <p>
          In the past, Select2 has only supported declaring a subset of options
          using <code>data-*</code> attributes. Select2 now supports declaring all
          options using the attributes, using
          <a href="options.html#data-attributes">the format specified in the documentation</a>.
        </p>

        <p>
          You could previously declare the URL that was used for AJAX requests using
          the <code>data-ajax-url</code> attribute. While Select2 still allows for
          this, the new attribute that should be used is the
          <code>data-ajax--url</code> attribute. Support for the old attribute will
          be removed in Select2 4.1.
        </p>

        <p>
          Although it was not documented, a list of possible tags could also be
          provided using the <code>data-select2-tags</code> attribute and passing in
          a JSON-formatted array of objects for tags. As the method for specifying
          tags has changed in 4.0, you should now provide the array of objects using
          the <code>data-data</code> attribute, which maps to
          <a href="options.html#data">the array data</a> option. You should also
          enable tags by setting <code>data-tags="true"</code> on the object, to
          maintain the ability for users to create their own options as well.
        </p>

        <p>
          If you previously declared the list of tags as…
        </p>

{% highlight html linenos %}
<select data-select2-tags='[{"id": "1", "text": "One"}, {"id": "2", "text": "Two"}]'></select>
{% endhighlight %}

        <p>
          …then you should now declare it as…
        </p>

{% highlight html linenos %}
<select data-data='[{"id": "1", "text": "One"}, {"id": "2", "text": "Two"}]' data-tags="true"></select>
{% endhighlight %}

        <h2 id="removed-methods">Deprecated and removed methods</h2>

        <p>
          As Select2 now uses a <code>&lt;select&gt;</code> element for all data
          sources, a few methods that were available by calling
          <code>.select2()</code> are no longer required.
        </p>

        <h3>.select2("val")</h3>

        <p>
          The <code>"val"</code> method has been deprecated and will be removed in
          Select2 4.1. The deprecated method no longer includes the
          <code>triggerChange</code> parameter.
        </p>

        <p>
          You should directly call <code>.val</code> on the underlying
          <code>&lt;select&gt;</code> element instead. If you needed the second
          parameter (<code>triggerChange</code>), you should also call
          <code>.trigger("change")</code> on the element.
        </p>

{% highlight js linenos %}
$("select").val("1").trigger("change"); // instead of $("select").select2("val", "1");
{% endhighlight %}

        <h3>.select2("enable")</h3>

        <p>
          Select2 will respect the <code>disabled</code> property of the underlying
          select element. In order to enable or disable Select2, you should call
          <code>.prop('disabled', true/false)</code> on the
          <code>&lt;select&gt;</code> element. Support for the old methods will be
          completely removed in Select2 4.1.
        </p>

{% highlight js linenos %}
$("select").prop("disabled", true); // instead of $("select").enable(false);
{% endhighlight %}

      </section>
    </div>
    <div class="col-md-3" role="complementary">

      {% include nav/announcements-4.0.html %}

    </div>
  </div>
</div>