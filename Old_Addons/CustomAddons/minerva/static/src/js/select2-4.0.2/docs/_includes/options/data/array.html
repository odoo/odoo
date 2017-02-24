<section>
  <h2 id="data">
    Can I load data into Select2 using an array?
  </h2>

  <p>
    While Select2 is designed to be used with a <code>&lt;select&gt;</code> tag
    the data that is used to search through and display the results can be
    loaded from a JavaScript array using the <code>data</code> option. This
    option should be passed in during the initialization of Select2.
  </p>

{% highlight js linenos %}
$('select').select2({
  data: [
    {
      id: 'value',
      text: 'Text to display'
    },
    // ... more data objects ...
  ]
});
{% endhighlight %}

  <h3>
    What properties are required on the objects passed in to the array?
  </h3>

  <p>
    The <code>id</code> and <code>text</code> properties are required on each
    object, and these are the properties that Select2 uses for the internal
    data objects. Any additional paramters passed in with data objects will be
    included on the data objects that Select2 exposes.
  </p>

  <h3>
    Do the <code>id</code> properties have to be strings?
  </h3>

  <p>
    Because the <code>value</code> attributes on a <code>&gt;select&lt;</code>
    tag must be strings, the <code>id</code> property on the data objects must
    also be strings. Select2 will attempt to convert anything that is not a
    string to a string, which will work for most situations, but it is
    recommended to force all of your ids to strings ahead of time.
  </p>

  <h3>
    I can't select results with blank ids or an id of <code>0</code>!
  </h3>

  <p>
    See <a href="#do-the-id-properties-have-to-be-strings">Do the <code>id</code> properties have to be strings?</a>.
  </p>

  <h3>
    How should nested results be formatted?
  </h3>

  <p>
    Nested results should be specified using the <code>children</code> property
    on the data objects that are passed in. This <code>children</code> property
    should be an array of data objects that are grouped under this option, and
    the label for the group should be specified as the <code>text</code>
    property on the root data object.
  </p>

{% highlight js linenos %}
{
  text: 'Group label',
  children: [
    {
      id: 'nested-1',
      text: 'First nested option'
    },
    // ... more data objects ...
  ]
}
{% endhighlight %}

  <h3>
    How many levels of nesting are allowed?
  </h3>

  <p>
    Because Select2 falls back to an <code>&lt;optgroup&gt;</code> when
    creating nested options, only
    <a href="#how-many-levels-of-nesting-can-there-be">a single level of nesting</a>
    is supported. Any additional levels of nesting is not guarenteed to be
    displayed properly across all browsers and devices.
  </p>

  <h3>
    Why are <code>&lt;option&gt;</code> tags being created?
  </h3>

  <p>
    The <code>data</code> option is a shortcut that Select2 provides which
    allows you to load options into your <code>select</code> from a data array.
  </p>

  {% include options/not-written.html %}

  <h3>
    My objects don&apos;t use <code>id</code> for their unique identifiers,
    what can I do?
  </h3>

  <p>
    Select2 requires that the <code>id</code> property is used to uniquely
    identify the options that are displayed in the results list. If you use a
    property other than <code>id</code> (like <code>pk</code>) to uniquely
    identify an option, you need to map your old property to <code>id</code>
    before passing it to Select2.
  </p>

  <p>
    If you cannot do this on your server or you are in a situation where the
    identifier cannot be changed, you can do this in JavaScript before passing
    it to Select2.
  </p>

{% highlight js linenos %}
var data = $.map(yourArrayData, function (obj) {
  obj.id = obj.id || obj.pk; // replace pk with your identifier

  return obj;
});
{% endhighlight %}

  <h3>
    My objects use a property other than <code>text</code> for the text that
    needs to be displayed
  </h3>

  <p>
    Just like with the <code>id</code> property, Select2 requires that the text
    that should be displayed for an option is stored in the <code>text</code>
    property. You can map this property from any existing property using the
    following JavaScript.
  </p>

{% highlight js linenos %}
var data = $.map(yourArrayData, function (obj) {
  obj.text = obj.text || obj.name; // replace name with the property used for the text

  return obj;
});
{% endhighlight %}
</section>