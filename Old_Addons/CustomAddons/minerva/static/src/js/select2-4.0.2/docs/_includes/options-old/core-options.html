<section>
  <h1 id="core-options" class="page-header">Core options</h1>

  <p>
    Select2 supports a small subset of options in every build that is
    generated. Each option typically has a decorator that is required that
    wraps an adapter, adding support for the option. This is only required
    when a custom adapter is being used, as Select2 will build the required
    adapters by default.
  </p>

  <p>
    Select2 will automatically apply decorators to any adapters which have not
    been manually overridden. The only time you need to decorate adapters is
    when you are using third-party adapters not provided by Select2, or you
    are using features not provided in the Select2 core. You can apply a
    decorator to an adapter using the
    <code title="select2/utils">Utils.Decorate</code> method provided with
    Select2.
  </p>

<pre class="prettyprint linenums">
$.fn.select2.amd.require(
    ["select2/utils", "select2/selection/single", "select2/selection/placeholder"],
    function (Utils, SingleSelection, Placeholder) {
  var CustomSelectionAdapter = Utils.Decorate(SingleSelection, Placeholder);
});
</pre>

  <p>
    All core options that use decorators or adapters will clearly state it
    in the "Decorator" or "Adapter" part of the documentation. Decorators are
    typically only compatible with a specific type of adapter, so make sure to
    note what adapter is given.
  </p>

  <h2 id="data-attributes">
    Declaring configuration in the <code>data-*</code> attributes
  </h2>

  <p>
    It is recommended that you declare your configuration options for Select2
    when initializing Select2. You can also define your configuration options
    by using the HTML5 <code>data-*</code> attributes, which will override
    any options set when initializing Select2 and any defaults.
  </p>

  <p>
    This means that if you declare your <code>&lt;select&gt;</code> tag as...
  </p>

<pre class="prettyprint">
&lt;select data-tags="true" data-placeholder="Select an option"&gt;&lt;/select&gt;
</pre>

  <p>
    Will be interpreted the same as initializing Select2 as...
  </p>

<pre class="prettyprint linenums">
$("select").select2({
  tags: "true",
  placeholder: "Select an option"
});
</pre>

  <p>
    You can also define nested configurations, which are typically needed for
    options such as AJAX. Each level of nesting should be separated by two
    dashes (<code>--</code>) instead of one. Due to
    <a href="https://github.com/jquery/jquery/issues/2070">a jQuery bug</a>,
    nested options using <code>data-*</code> attributes
    <a href="https://github.com/select2/select2/issues/2969">do not work in jQuery 1.x</a>.
  </p>

<pre class="prettyprint">
&lt;select data-ajax--url="http://example.org/api/test" data-ajax--cache="true"&gt;&lt;/select&gt;
</pre>

  <p>
    Which will be interpreted the same as initializing Select2 with...
  </p>

<pre class="prettyprint linenums">
$("select").select2({
  ajax: {
    url: "http://example.org/api/test",
    cache: "true"
  }
});
</pre>

  <p>
    The value of the option is subject to jQuery's
    <a href="https://api.jquery.com/data/#data-html5">parsing rules</a> for
    HTML5 data attributes.
  </p>

  <h2 id="amd">
    AMD compatibility
  </h2>

  <p>
    You can find more information on how to integrate Select2 with your
    existing AMD-based project by
    <a href="announcements-4.0.html#builds">viewing the 4.0 release notes</a>.
    Select2 automatically loads some modules when the adapters are being
    automatically constructed, so those who are using Select2 with a custom
    AMD build using their own system may need to specify the paths that are
    generated to the Select2 modules.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd>
          <code>amdBase</code>
        </dd>

        <dt>Default</dt>
        <dd>
          <code>select2/</code>
        </dd>
      </dl>
    </div>
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd>
          <code>amdLanguageBase</code>
        </dd>

        <dt>Default</dt>
        <dd>
          <code>select2/i18n/</code>
        </dd>
      </dl>
    </div>
  </div>

  <h2 id="core-options-display">
    Displaying selections
  </h2>

  <p>
    Select2 provides options that allow you to directly affect how the
    container that holds the current selection is displayed.
  </p>

  <h3 id="placeholder">
    Placeholders
  </h3>

  <p>
    Select2 can display a placeholder for a single-value select that will
    replace an option, or be shown when no options are selected for
    multiple-value selects. You can find an example on the
    <a href="examples.html#placeholders">example page</a>.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd>
          <code>placeholder</code>
        </dd>

        <dt>Value</dt>
        <dd>string or object</dd>
      </dl>

      <hr />

      <dl class="dl-horizontal">
        <dt>Adapter</dt>
        <dd>
          <code title="select2/selection/base">SelectionAdapter</code>
        </dd>

        <dt>Decorator</dt>
        <dd>
          <code title="select2/selection/placeholder">Placeholder</code>
          and
          <code title="select2/dropdown/hidePlaceholder">HidePlaceholder</code>
        </dd>
      </dl>
    </div>

    <div class="col-sm-6">
      <div class="alert alert-warning">
        <strong>Heads up!</strong>
        Because browsers assume that the first <code>option</code> in
        single-value select boxes is selected, you should add an empty
        <code>&lt;option&gt;&lt;/option&gt;</code> tag that the placeholder
        should use or it may not work.
      </div>
    </div>
  </div>

  <p>
    If the <strong>value is a string</strong>, the placeholder will be
    displayed when a <strong>blank option</strong> is used as the placeholder.
    The <strong>value</strong> will be the message to show to users as the
    placeholders.
  </p>

<pre class="prettyprint">
placeholder: "Select a repository"
</pre>

      <p>
        If the <strong>value is an object</strong>, the object should be
        compatible with Select2's internal objects. The <code>id</code> should
        be the id to look for when determining if the placeholder should be
        displayed. The <code>text</code> should be the placeholder to display
        when that option is selected.
      </p>

<pre class="prettyprint linenums">
placeholder: {
  id: "-1",
  text: "Select a repository"
}
</pre>

  <div class="alert alert-info">
    You should <strong>pass in an object</strong> when you are using a
    framework that <strong>creates its own placeholder option</strong>. The
    <strong>id</strong> should be the same as the <code>value</code>
    attribute on the <code>option</code>.
  </div>

  <p id="allowClear">
    You can allow a selected option to be cleared back to the placeholder by
    enabling the <code>allowClear</code> option.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd><code>allowClear</code></dd>

        <dt>Value</dt>
        <dd>boolean</dd>
      </dl>
    </div>

    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Adapter</dt>
        <dd>
          <code title="select2/selection/base">SelectionAdapter</code>
        </dd>

        <dt>Decorator</dt>
        <dd>
          <code title="select2/selection/allowClear">AllowClear</code>
        </dd>
      </dl>
    </div>
  </div>

  <p>
    This will display an "x" that the user can click to clear the current
    selection. It is designed to be used for cases where a single selection
    can be made.
  </p>

  <h3 id="multiple">
    Multiple selections
  </h3>

  <p>
    Select2 can display either a single selection or multiple selections.
  </p>

  <dl class="dl-horizontal">
    <dt>Key</dt>
    <dd><code>multiple</code></dd>

    <dt>Value</dt>
    <dd>boolean (<code>true</code> or <code>false</code>)</dd>
  </dl>

  <p>
    This option will determine what the <code>SelectAdapter</code> (used by
    default) should use to set the value of the underlying <code>select</code>
    element. It will also determine if the <code>MultipleSelection</code>
    adapter should be used.
  </p>

  <h3 id="width">
    Container width
  </h3>

  <p>
    Select2 will try to match the width of the original element as closely as
    possible. Sometimes this isn't perfect, which is what you can tell Select2
    how to determine the width.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <table class="table table-striped table-bordered">
        <thead>
          <tr>
            <th>Value</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>"element"</code></td>
            <td>
              Uses javascript to calculate the width of the source element.
            </td>
          </tr>
          <tr>
            <td><code>"style"</code></td>
            <td>
              Copies the value of the width <code>style</code> attribute set on the source element.
            </td>
          </tr>
          <tr>
            <td><code>"resolve"</code></td>
            <td>
              Tries to use <code>style</code> to determine the width, falling back to <code>element</code>.
            </td>
          </tr>
          <tr>
            <td>Anything else</td>
            <td>
              The value of the <code>width</code> option is directly set as the width of the container.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd><code>width</code></dd>

        <dt>Value</dt>
        <dd>string</dd>
      </dl>
    </div>
  </div>

  <h3 id="language">
    Internationalization (Language support)
  </h3>

  <p>
    Messages will be displayed to users when necessary, such as when no
    search results were found or more characters need to be entered in order
    for a search to be made. These messages have been
    <a href="community.html#translations">translated into many languages</a>
    by contributors to Select2, but you can also provide your own
    translations.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd><code>language</code></dd>

        <dt>Value</dt>
        <dd>object or string</dd>
      </dl>

      <hr />

      <dl class="dl-horizontal">
        <dt>Module</dt>
        <dd>
          <code title="select2/translation">Translation</code>
        </dd>
      </dl>
    </div>

    <div class="col-sm-6">
      <p class="alert alert-warning">
        <strong>Heads up!</strong> When using translations provided by Select2,
        you must make sure to include the translation file in your page after
        Select2.
      </p>
    </div>
  </div>

  <p>
    When a string is passed in as the language, Select2 will try to resolve
    it into a language file. This allows you to specify your own language
    files, which must be defined as an AMD module. If the language file
    cannot be found, Select2 will assume it is a language code controlled by
    Select2, and it will try to load the translations for that language
    instead.
  </p>

  <p>
    You can include your own translations by providing an object similar to
    the one below.
  </p>

<pre class="prettyprint linenums">
language: {
  // You can find all of the options in the language files provided in the
  // build. They all must be functions that return the string that should be
  // displayed.
  inputTooShort: function () {
    return "You must enter more characters...";
  }
}
</pre>

  <h3 id="templating">
    Templating results and selections
  </h3>

  <p>
    By default, Select2 will display the option text within the list of
    results and when the option has been selected.  Select2 comes with options
    that allow you to further customize the display of results and selections,
    allowing you to display them however you want.
  </p>

  <h4 id="templateSelection">
    Customizing the display of selections
  </h4>

  <p>
    When an option is displayed after it has been selected, it is passed
    through a formatting function that determines what is displayed. By
    default, the function only returns the <code>text</code> key of the data
    object.
  </p>

  <dl class="dl-horizontal">
    <dt>Key</dt>
    <dd><code>templateSelection</code></dd>

    <dt>Value</dt>
    <dd>A function taking a <code>selection</code> object</dd>
  </dl>

  <div class="alert alert-info">
    <strong>Anything rendered as a selection is templated.</strong>
    This includes placeholders and pre-existing selections that are displayed,
    so you must ensure that your templating functions can support them.
  </div>

  <p>
    The <code>templateSelection</code> function should return a string
    containing the text to be displayed, or an object (such as a jQuery
    object) that contains the data that should be displayed.
  </p>

  <p>
    <strong>Strings are assumed to contain only text</strong> and will be
    passed through the <code>escapeMarkup</code> function, which strips any
    HTML markup.
  </p>

  <p>
    <strong>
      Anything else will be passed
      <a href="https://api.jquery.com/append/">directly to <code>jQuery.fn.append</code></a>
    </strong> and will be handled directly by jQuery.  Any markup, such as
    HTML, returned will not be escaped and it is up to you to escape any
    malicious input provided by users.
  </p>

  <h4 id="templateResult">
    Customizing the display of results
  </h4>

  <p>
    When an option is displayed after it has been selected, it is passed
    through a formatting function that determines what is displayed. By
    default, the function only returns the <code>text</code> key of the data
    object.
  </p>

  <dl class="dl-horizontal">
    <dt>Key</dt>
    <dd><code>templateResult</code></dd>

    <dt>Value</dt>
    <dd>A function taking a <code>result</code> object</dd>
  </dl>

  <div class="alert alert-info">
    <strong>Anything rendered in the results is templated.</strong>
    This includes results such as the "Searching..." and "Loading more..."
    text which will periodically be displayed, which allows you to add more
    advanced formatting to these automatically generated options.
  </div>

  <p>
    The <code>templateResult</code> function should return a string
    containing the text to be displayed, or an object (such as a jQuery
    object) that contains the data that should be displayed.  It can also
    return <code>null</code>, which will prevent the option from being
    displayed in the results list.
  </p>

  <p>
    <strong>Strings are assumed to contain only text</strong> and will be
    passed through the <code>escapeMarkup</code> function, which strips any
    HTML markup.
  </p>

  <p>
    <strong>
      Anything else will be passed
      <a href="https://api.jquery.com/append/">directly to <code>jQuery.fn.append</code></a>
    </strong> and will be handled directly by jQuery.  Any markup, such as
    HTML, returned will not be escaped and it is up to you to escape any
    malicious input provided by users.
  </p>

  <h2 id="core-options-results">
    Returning and displaying results
  </h2>

  <p>
    Select2 can work on many different data sets ranging from local options,
    the same way that a <code>&lt;select&gt;</code> typically works, from
    remote options where a server generates the results that users can select
    from.
  </p>

  <h3 id="data">
    Array
  </h3>

  <p>
    Select2 allows creating the results based on an array of data objects that
    is included when initializing Select2.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd><code>data</code></dd>

        <dt>Value</dt>
        <dd>array of objects</dd>
      </dl>
    </div>

    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Adapter</dt>
        <dd>
          <code title="select2/data/array">ArrayAdapter</code>
        </dd>
      </dl>
    </div>
  </div>

  <p>
    The objects that the users can select from should be passed as an array
    with each object containing <code>id</code> and <code>text</code>
    properties.
  </p>

  <h3 id="ajax">
    AJAX
  </h3>

  <p>
    Select2 allows searching for results from remote data sources using AJAX
    requests.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd><code>ajax</code></dd>

        <dt>Value</dt>
        <dd>object</dd>
      </dl>
    </div>

    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Adapter</dt>
        <dd>
          <code title="select2/data/ajax">AjaxAdapter</code>
        </dd>
      </dl>
    </div>
  </div>

  <p>
    All options passed to this option will be directly passed to the
    <code>$.ajax</code> function that executes AJAX requests. There are a few
    custom options that Select2 will intercept, allowing you to customize the
    request as it is being made.

<pre class="prettyprint linenums">
ajax: {
  // The number of milliseconds to wait for the user to stop typing before
  // issuing the ajax request.
  delay: 250,
  // You can craft a custom url based on the parameters that are passed into the
  // request. This is useful if you are using a framework which has
  // JavaScript-based functions for generating the urls to make requests to.
  //
  // @param params The object containing the parameters used to generate the
  //   request.
  // @returns The url that the request should be made to.
  url: function (params) {
    return UrlGenerator.Random();
  },
  // You can pass custom data into the request based on the parameters used to
  // make the request. For `GET` requests, the default method, these are the
  // query parameters that are appended to the url. For `POST` requests, this
  // is the form data that will be passed into the request. For other requests,
  // the data returned from here should be customized based on what jQuery and
  // your server are expecting.
  //
  // @param params The object containing the parameters used to generate the
  //   request.
  // @returns Data to be directly passed into the request.
  data: function (params) {
    var queryParameters = {
      q: params.term
    }

    return queryParameters;
  },
  // You can modify the results that are returned from the server, allowing you
  // to make last-minute changes to the data, or find the correct part of the
  // response to pass to Select2. Keep in mind that results should be passed as
  // an array of objects.
  //
  // @param data The data as it is returned directly by jQuery.
  // @returns An object containing the results data as well as any required
  //   metadata that is used by plugins. The object should contain an array of
  //   data objects as the `results` key.
  processResults: function (data) {
    return {
      results: data
    };
  },
  // You can use a custom AJAX transport function if you do not want to use the
  // default one provided by jQuery.
  //
  // @param params The object containing the parameters used to generate the
  //   request.
  // @param success A callback function that takes `data`, the results from the
  //   request.
  // @param failure A callback function that indicates that the request could
  //   not be completed.
  // @returns An object that has an `abort` function that can be called to abort
  //   the request if needed.
  transport: function (params, success, failure) {
    var $request = $.ajax(params);

    $request.then(success);
    $request.fail(failure);

    return $request;
  }
}
</pre>
  </p>

  <h3 id="tags">
    Tags
  </h3>

  <p>
    Users can create their own options based on the text that they have
    entered.
  </p>

  <div class="row">
    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Key</dt>
        <dd><code>tags</code></dd>

        <dt>Value</dt>
        <dd>boolean / array of objects</dd>
      </dl>
    </div>

    <div class="col-sm-6">
      <dl class="dl-horizontal">
        <dt>Adapter</dt>
        <dd>
          <code title="select2/data/base">DataAdapter</code>
        </dd>

        <dt>Decorator</dt>
        <dd>
          <code title="select2/data/tags">Tags</code>
        </dd>
      </dl>
    </div>
  </div>

  <p>
    If the <code>tags</code> option is passed into Select2, if a user types
    anything into the search box which doesn't already exist, it will be
    displayed at the top and the user will be able to select it.
  </p>

  <p>
    <strong>For backwards compatibility</strong>, if an array of objects is
    passed in with the <code>tags</code> option, the options will be
    automatically created and the user will be able to select from them.
    This is the <strong>same as how <a href="#data">array data</a>
    works</strong>, and has similar limitations.
  </p>

  <h3 id="matcher">
    Change how options are matched when searching
  </h3>

  <p>
    When users filter down the results by entering search terms into the
    search box, Select2 uses an internal "matcher" to match search terms to
    results. <strong>When a remote data set is used, Select2 expects that the
    returned results have already been filtered.</strong>
  </p>

  <dl class="dl-horizontal">
    <dt>Key</dt>
    <dd>
      <code>matcher</code>
    </dd>

    <dt>Value</dt>
    <dd>
      A function taking search <code>params</code> and the
      <code>data</code> object.
    </dd>
  </dl>

  <p>
    Select2 will pass the individual data objects that have been passed back
    from the data adapter into the <code>matcher</code> individually to
    determine if they should be displayed. Only the first-level objects will
    be passed in, so <strong>if you are working with nested data, you need to
    match those individually</strong>.
  </p>

<pre class="prettyprint linenums">
matcher: function (params, data) {
  // If there are no search terms, return all of the data
  if ($.trim(params.term) === '') {
    return data;
  }

  // `params.term` should be the term that is used for searching
  // `data.text` is the text that is displayed for the data object
  if (data.text.indexOf(params.term) > -1) {
    var modifiedData = $.extend({}, data, true);
    modifiedData.text += ' (matched)';

    // You can return modified objects from here
    // This includes matching the `children` how you want in nested data sets
    return modifiedData;
  }

  // Return `null` if the term should not be displayed
  return null;
}
</pre>

  <p>
    This allows for more advanced matching when working with nested objects,
    allowing you to handle them however you want. For those who are not
    looking to implement highly customized matching, but instead are just
    looking to change the matching algorithm for the text, a
    <a href="#compat-matcher">compatibility modules</a> has been created to
    make it easier.
  </p>
</section>
