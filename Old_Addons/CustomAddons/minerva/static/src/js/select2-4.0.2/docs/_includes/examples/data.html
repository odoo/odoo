<section>

  <h1 id="data" class="page-header">
    Data sources
  </h1>

  <p>In addition to handling options from a standard <code>&lt;select&gt;</code>, Select2 can also retrieve the results from other data sources.</p>

  <h2 id="data-array" >Loading array data</h2>

  <p>
    Select2 provides a way to load the data from a local array.
    You can provide initial selections with array data by providing the
    option tag for the selected values, similar to how it would be done for
    a standard select.
  </p>

  <div class="s2-example">
    <p>
      <select class="js-example-data-array form-control"></select>
    </p>
    <p>
      <select class="js-example-data-array-selected form-control">
        <option value="2" selected="selected">duplicate</option>
      </select>
    </p>
  </div>

{% highlight html linenos %}
<script type="text/javascript">
var data = [{ id: 0, text: 'enhancement' }, { id: 1, text: 'bug' }, { id: 2, text: 'duplicate' }, { id: 3, text: 'invalid' }, { id: 4, text: 'wontfix' }];

$(".js-example-data-array").select2({
  data: data
})

$(".js-example-data-array-selected").select2({
  data: data
})
</script>

<select class="js-example-data-array"></select>

<select class="js-example-data-array-selected">
  <option value="2" selected="selected">duplicate</option>
</select>
{% endhighlight %}

  <h2 id="data-ajax" >Loading remote data</h2>

  <p>
    Select2 comes with AJAX support built in, using jQuery's AJAX methods.
    In this example, we can search for repositories using GitHub's API.
  </p>

  <p>
    <select class="js-example-data-ajax form-control">
      <option value="3620194" selected="selected">select2/select2</option>
    </select>
  </p>

  <p>
    When using Select2 with remote data, the HTML required for the
    <code>select</code> is the same as any other Select2. If you need to
    provide default selections, you just need to include an
    <code>option</code> for each selection that contains the value and text
    that should be displayed.
  </p>

{% highlight html linenos %}
<select class="js-data-example-ajax">
  <option value="3620194" selected="selected">select2/select2</option>
</select>
{% endhighlight %}

  <p>
    You can configure how Select2 searches for remote data using the
    <code>ajax</code> option. More information on the individual options
    that Select2 handles can be found in the
    <a href="options.html#ajax">options documentation for <code>ajax</code></a>.
  </p>

{% highlight js linenos %}
$(".js-data-example-ajax").select2({
  ajax: {
    url: "https://api.github.com/search/repositories",
    dataType: 'json',
    delay: 250,
    data: function (params) {
      return {
        q: params.term, // search term
        page: params.page
      };
    },
    processResults: function (data, params) {
      // parse the results into the format expected by Select2
      // since we are using custom formatting functions we do not need to
      // alter the remote JSON data, except to indicate that infinite
      // scrolling can be used
      params.page = params.page || 1;

      return {
        results: data.items,
        pagination: {
          more: (params.page * 30) < data.total_count
        }
      };
    },
    cache: true
  },
  escapeMarkup: function (markup) { return markup; }, // let our custom formatter work
  minimumInputLength: 1,
  templateResult: formatRepo, // omitted for brevity, see the source of this page
  templateSelection: formatRepoSelection // omitted for brevity, see the source of this page
});
{% endhighlight %}

  <p>
    Select2 will pass any options in the <code>ajax</code> object to
    jQuery's <code>$.ajax</code> function, or the <code>transport</code>
    function you specify.
  </p>
</section>
