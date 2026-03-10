export const templates = {
 "devtools.ContextMenu": function devtools_ContextMenu(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  
  let block1 = createBlock(`<div class="custom-menu" block-ref="0"><ul class="my-1"><block-child-0/></ul></div>`);
  let block4 = createBlock(`<li class="custom-menu-item py-1 px-4" block-handler-0="click.stop"><block-text-1/></li>`);
  
  return function template(ctx, node, key = "") {
    let ref1 = (el) => this.__owl__.setRef((`contextmenu`), el);
    ctx = Object.create(ctx);
    const [k_block2, v_block2, l_block2, c_block2] = prepareList(ctx['props'].items);;
    for (let i1 = 0; i1 < l_block2; i1++) {
      ctx[`item`] = k_block2[i1];
      ctx[`item_index`] = i1;
      const key1 = ctx['item_index'];
      let b4;
      if (ctx['item'].show) {
        const v1 = ctx['this'];
        const v2 = ctx['item'];
        let hdlr1 = ["stop", ()=>v1.onClickItem(v2.action), ctx];
        let txt1 = ctx['item'].title;
        b4 = block4([hdlr1, txt1]);
      }
      c_block2[i1] = withKey(multi([b4]), key1);
    }
    const b2 = list(c_block2);
    return block1([ref1], [b2]);
  }
},

"devtools.ComponentSearchBar": function devtools_ComponentSearchBar(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  
  let block2 = createBlock(`<div class="mouse-icon p-1" block-handler-0="click.stop"><i title="Select an element in the page to inspect the corresponding component" class="fa fa-fw fa-mouse-pointer" block-attribute-1="style"/></div>`);
  let block3 = createBlock(`<div class="icons-separator"/>`);
  let block4 = createBlock(`<div class="d-flex align-items-center ms-2 flex-grow-1"><i class="fa fa-search search-icon" aria-hidden="true"/><input type="text" class="search-input ms-1 w-100 border-0 h-100" placeholder="Search" block-property-0="value" block-handler-1="keyup.stop" block-handler-2="keydown.stop"/><block-child-0/></div>`);
  let block9 = createBlock(`<i class="fa fa-angle-up lg-icon utility-icon ms-1 p-1" block-handler-0="click.stop"/>`);
  let block10 = createBlock(`<i class="fa fa-angle-down lg-icon utility-icon p-1" block-handler-0="click.stop"/>`);
  let block11 = createBlock(`<i class="fa fa-times lg-icon utility-icon p-1 me-2" block-handler-0="click.stop"/>`);
  
  return function template(ctx, node, key = "") {
    const v1 = ctx['this'];
    let hdlr1 = ["stop", ()=>v1.store.toggleSelector(), ctx];
    let attr1 = `color: ${ctx['store'].componentSearch.activeSelector?'var(--active-icon)':'var(--text-color)'};`;
    const b2 = block2([hdlr1, attr1]);
    const b3 = block3();
    let b5;
    let prop1 = new String((ctx['store'].componentSearch.search) === 0 ? 0 : ((ctx['store'].componentSearch.search) || ""));
    let hdlr2 = ["stop", ctx['updateSearch'], ctx];
    let hdlr3 = ["stop", ctx['onSearchKeyDown'], ctx];
    if (ctx['store'].componentSearch.search.length>0) {
      const b6 = text(ctx['store'].componentSearch.searchResults.length?ctx['store'].componentSearch.searchIndex+1:0);
      const b7 = text(`|`);
      const b8 = text(ctx['store'].componentSearch.searchResults.length);
      const v2 = ctx['this'];
      let hdlr4 = ["stop", ()=>v2.store.componentSearch.getPrevSearch(), ctx];
      const b9 = block9([hdlr4]);
      const v3 = ctx['this'];
      let hdlr5 = ["stop", ()=>v3.store.componentSearch.getNextSearch(), ctx];
      const b10 = block10([hdlr5]);
      const v4 = ctx['this'];
      let hdlr6 = ["stop", ()=>v4.store.updateSearch(""), ctx];
      const b11 = block11([hdlr6]);
      b5 = multi([b6, b7, b8, b9, b10, b11]);
    }
    const b4 = block4([prop1, hdlr2, hdlr3], [b5]);
    return multi([b2, b3, b4]);
  }
},

"devtools.ComponentsTab": function devtools_ComponentsTab(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  const comp1 = app.createComponent(`ComponentSearchBar`, true, false, false, []);
  const comp2 = app.createComponent(`TreeElement`, true, false, false, ["component"]);
  const comp3 = app.createComponent(`DetailsWindow`, true, false, false, []);
  
  let block2 = createBlock(`<div class="status-message d-flex justify-content-center align-items-center"> There are no apps currently running. </div>`);
  let block3 = createBlock(`<div class="position-relative overflow-hidden d-flex flex-row h-100"><div class="split-screen-left d-flex flex-column" block-attribute-0="style"><div class="panel-top d-flex align-items-center"><block-child-0/></div><div class="overflow-auto h-100 font-monospace"><div id="tree-wrapper"><block-child-1/></div></div></div><div class="split-screen-border user-select-none" block-handler-1="mousedown"/><div class="split-screen-right d-flex flex-column font-monospace" block-attribute-2="style"><block-child-2/><block-child-3/></div></div>`);
  let block8 = createBlock(`<div class="status-message d-flex justify-content-center align-items-center"> There was an error while processing this component. </div>`);
  
  return function template(ctx, node, key = "") {
    let b2, b3;
    if (ctx['store'].apps.length===0) {
      b2 = block2();
    } else {
      let b4, b5, b7, b8;
      let attr1 = `width:${ctx['store'].splitPosition}%;`;
      b4 = comp1({}, key + `__1`, node, this, null);
      ctx = Object.create(ctx);
      const [k_block5, v_block5, l_block5, c_block5] = prepareList(ctx['store'].apps);;
      for (let i1 = 0; i1 < l_block5; i1++) {
        ctx[`app`] = k_block5[i1];
        ctx[`app_index`] = i1;
        const key1 = ctx['app_index'];
        c_block5[i1] = withKey(comp2({component: ctx['app']}, key + `__2__${key1}`, node, this, null), key1);
      }
      ctx = ctx.__proto__;
      b5 = list(c_block5);
      let hdlr1 = [ctx['onMouseDown'], ctx];
      let attr2 = `width:${100-ctx['store'].splitPosition}%;`;
      if (ctx['store'].activeComponent) {
        b7 = comp3({}, key + `__3`, node, this, null);
      } else {
        b8 = block8();
      }
      b3 = block3([attr1, hdlr1, attr2], [b4, b5, b7, b8]);
    }
    return multi([b2, b3]);
  }
},

"devtools.DetailsWindow": function devtools_DetailsWindow(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  const comp1 = app.createComponent(`ObjectTreeElement`, true, false, false, ["object","index"]);
  const comp2 = app.createComponent(`ObjectTreeElement`, true, false, false, ["object"]);
  const comp3 = app.createComponent(`ObjectTreeElement`, true, false, false, ["object"]);
  const comp4 = app.createComponent(`ObjectTreeElement`, true, false, false, ["object"]);
  const comp5 = app.createComponent(`ObjectTreeElement`, true, false, false, ["object"]);
  const comp6 = app.createComponent(`ObjectTreeElement`, true, false, false, ["object"]);
  
  let block2 = createBlock(`<div class="panel-top d-flex align-items-center"><div class="ms-1 p-1 text-truncate" style="width: 100%;"><block-child-0/><b style="color: var(--component-color); cursor: pointer;" block-handler-0="mouseover.stop" block-handler-1="click.stop" block-handler-2="contextmenu.prevent"><block-text-3/></b><block-child-1/><block-child-2/></div><block-child-3/><block-child-4/></div>`);
  let block3 = createBlock(`<span>&lt;</span>`);
  let block4 = createBlock(`<span>&gt;</span>`);
  let block5 = createBlock(`<span class="version">owl=<block-text-0/></span>`);
  let block7 = createBlock(`<i title="Inspect component in the Elements tab" class="fa fa-eye utility-icon p-1" block-handler-0="click.stop"/>`);
  let block8 = createBlock(`<i title="Store component as global variable in the console" class="fa fa-bug utility-icon p-1" block-handler-0="click.stop"/>`);
  let block9 = createBlock(`<i title="Inspect source code of component" class="fa fa-file-code-o utility-icon p-1" block-handler-0="click.stop"/>`);
  let block10 = createBlock(`<i title="Trigger rerender of the component" class="fa fa-refresh utility-icon p-1" block-handler-0="click.stop"/>`);
  let block12 = createBlock(`<i title="Store app as global variable in the console" class="fa fa-bug utility-icon p-1" block-handler-0="click.stop"/>`);
  let block13 = createBlock(`<i title="Inspect source code of the app" class="fa fa-file-code-o utility-icon p-1" block-handler-0="click.stop"/>`);
  let block14 = createBlock(`<div class="details-container"><block-child-0/><block-child-1/><block-child-2/><block-child-3/><block-child-4/><block-child-5/></div>`);
  let block15 = createBlock(`<div id="observedVariables" class="details-panel ps-2 py-1"><div class="d-flex mb-2"><div class="w-100"><b class="ps-2">observed variables</b></div><i title="Remove observed variables" class="fa fa-times utility-icon p-1" block-handler-0="click.stop"/></div><block-child-0/></div>`);
  let block19 = createBlock(`<div id="env" class="details-panel ps-2 py-1"><div class="d-flex mb-2"><div class="w-100" block-handler-0="click.stop"><i class="fa mx-1 pointer-icon" block-attribute-1="class"/><b>env</b></div></div><block-child-0/></div>`);
  let block23 = createBlock(`<div class="details-panel ps-2 py-1"><div class="d-flex mb-2"><div class="w-100" block-handler-0="click.stop"><i class="fa mx-1 pointer-icon" block-attribute-1="class"/><b>props</b></div></div><block-child-0/></div>`);
  let block27 = createBlock(`<div id="subscriptions" class="details-panel ps-2 py-1"><div class="d-flex"><div title="Shows all the targets that will trigger a re-render of the component when one of its associated keys is modified" class="w-100 text-truncate" block-handler-0="click.stop"><i class="fa mx-1 pointer-icon" block-attribute-1="class"/><b>observed state</b></div><i title="Store observed states as global variable in the console" class="fa fa-bug utility-icon p-1" block-handler-2="click.stop"/></div><block-child-0/></div>`);
  let block28 = createBlock(`<div id="subscriptionsPanel"><block-child-0/></div>`);
  let block31 = createBlock(`<div id="instance" class="details-panel ps-2 py-1"><div class="d-flex mb-2"><div class="w-100 text-truncate" block-handler-0="click.stop"><i class="fa mx-1 pointer-icon" block-attribute-1="class"/><b>instance</b></div><block-child-0/></div><block-child-1/></div>`);
  let block33 = createBlock(`<i title="Inspect compiled template" class="fa fa-hashtag utility-icon p-1" block-handler-0="click.stop"/>`);
  let block34 = createBlock(`<i title="Send raw template to console" class="fa fa-file-word-o utility-icon p-1" block-handler-0="click.stop"/>`);
  let block38 = createBlock(`<div id="hooks" class="details-panel ps-2 py-1"><div class="d-flex mb-2"><div class="w-100" block-handler-0="click.stop"><i class="fa mx-1 pointer-icon" block-attribute-1="class"/><b>hooks</b></div><i title="Remove breakpoints" class="fa fa-times utility-icon p-1" block-handler-2="click.stop"/></div><block-child-0/></div>`);
  
  return function template(ctx, node, key = "") {
    let b3, b4, b5, b6, b11;
    if (ctx['store'].activeComponent.path.length>1) {
      b3 = block3();
    }
    const v1 = ctx['this'];
    let hdlr1 = ["stop", ()=>v1.store.highlightComponent(v1.store.activeComponent.path), ctx];
    const v2 = ctx['this'];
    let hdlr2 = ["stop", ()=>v2.store.onActiveComponentClick(), ctx];
    let hdlr3 = ["prevent", ctx['openMenu'], ctx];
    let txt1 = ctx['store'].activeComponent.name;
    if (ctx['store'].activeComponent.path.length>1) {
      b4 = block4();
    } else {
      let txt2 = ctx['store'].activeComponent.version;
      b5 = block5([txt2]);
    }
    if (ctx['store'].activeComponent.path.length>1) {
      const v3 = ctx['this'];
      let hdlr4 = ["stop", ()=>v3.store.inspectComponent('DOM'), ctx];
      const b7 = block7([hdlr4]);
      const v4 = ctx['this'];
      let hdlr5 = ["stop", ()=>v4.store.logObjectInConsole(), ctx];
      const b8 = block8([hdlr5]);
      const v5 = ctx['this'];
      let hdlr6 = ["stop", ()=>v5.store.inspectComponent('source'), ctx];
      const b9 = block9([hdlr6]);
      const v6 = ctx['this'];
      let hdlr7 = ["stop", ()=>v6.store.refreshComponent(), ctx];
      const b10 = block10([hdlr7]);
      b6 = multi([b7, b8, b9, b10]);
    } else {
      const v7 = ctx['this'];
      let hdlr8 = ["stop", ()=>v7.store.logObjectInConsole(), ctx];
      const b12 = block12([hdlr8]);
      const v8 = ctx['this'];
      let hdlr9 = ["stop", ()=>v8.store.inspectComponent('source'), ctx];
      const b13 = block13([hdlr9]);
      b11 = multi([b12, b13]);
    }
    const b2 = block2([hdlr1, hdlr2, hdlr3, txt1], [b3, b4, b5, b6, b11]);
    let b15, b19, b23, b27, b31, b38;
    if (ctx['store'].observedVariables.length&&ctx['store'].observedVariables.some((_v)=>_v.visible)) {
      const v9 = ctx['this'];
      let hdlr10 = ["stop", ()=>v9.store.clearObservedVariable(), ctx];
      ctx = Object.create(ctx);
      const [k_block16, v_block16, l_block16, c_block16] = prepareList(ctx['store'].observedVariables);;
      for (let i1 = 0; i1 < l_block16; i1++) {
        ctx[`observed`] = k_block16[i1];
        ctx[`observed_index`] = i1;
        const key1 = ctx['observed_index'];
        let b18;
        if (ctx['observed'].visible) {
          b18 = comp1({object: ctx['observed'],index: ctx['observed_index']}, key + `__1__${key1}`, node, this, null);
        }
        c_block16[i1] = withKey(multi([b18]), key1);
      }
      ctx = ctx.__proto__;
      const b16 = list(c_block16);
      b15 = block15([hdlr10], [b16]);
    }
    if (ctx['store'].activeComponent.env.children.length>0) {
      const v10 = ctx['this'];
      let hdlr11 = ["stop", (_ev)=>v10.toggleCategory(_ev,'env'), ctx];
      let attr1 = {'fa-caret-right':!ctx['store'].activeComponent.env.toggled,'fa-caret-down':ctx['store'].activeComponent.env.toggled};
      ctx = Object.create(ctx);
      const [k_block20, v_block20, l_block20, c_block20] = prepareList(ctx['store'].activeComponent.env.children);;
      for (let i1 = 0; i1 < l_block20; i1++) {
        ctx[`env`] = k_block20[i1];
        ctx[`env_index`] = i1;
        const key1 = ctx['env_index'];
        let b22;
        if (ctx['store'].activeComponent.env.toggled) {
          b22 = comp2({object: ctx['env']}, key + `__2__${key1}`, node, this, null);
        }
        c_block20[i1] = withKey(multi([b22]), key1);
      }
      ctx = ctx.__proto__;
      const b20 = list(c_block20);
      b19 = block19([hdlr11, attr1], [b20]);
    }
    if (ctx['store'].activeComponent.props.children.length>0) {
      const v11 = ctx['this'];
      let hdlr12 = ["stop", (_ev)=>v11.toggleCategory(_ev,'props'), ctx];
      let attr2 = {'fa-caret-right':!ctx['store'].activeComponent.props.toggled,'fa-caret-down':ctx['store'].activeComponent.props.toggled};
      ctx = Object.create(ctx);
      const [k_block24, v_block24, l_block24, c_block24] = prepareList(ctx['store'].activeComponent.props.children);;
      for (let i1 = 0; i1 < l_block24; i1++) {
        ctx[`prop`] = k_block24[i1];
        ctx[`prop_index`] = i1;
        const key1 = ctx['prop_index'];
        let b26;
        if (ctx['store'].activeComponent.props.toggled) {
          b26 = comp3({object: ctx['prop']}, key + `__3__${key1}`, node, this, null);
        }
        c_block24[i1] = withKey(multi([b26]), key1);
      }
      ctx = ctx.__proto__;
      const b24 = list(c_block24);
      b23 = block23([hdlr12, attr2], [b24]);
    }
    if (ctx['store'].activeComponent.subscriptions.children.length>0) {
      let b28;
      const v12 = ctx['this'];
      let hdlr13 = ["stop", (_ev)=>v12.toggleCategory(_ev,'subscriptions'), ctx];
      let attr3 = {'fa-caret-right':!ctx['store'].activeComponent.subscriptions.toggled,'fa-caret-down':ctx['store'].activeComponent.subscriptions.toggled};
      const v13 = ctx['this'];
      let hdlr14 = ["stop", ()=>v13.store.logObjectInConsole([...v13.store.activeComponent.path,{type:'item',value:'subscriptions'}]), ctx];
      if (ctx['store'].activeComponent.subscriptions.toggled) {
        ctx = Object.create(ctx);
        const [k_block29, v_block29, l_block29, c_block29] = prepareList(ctx['store'].activeComponent.subscriptions.children);;
        for (let i1 = 0; i1 < l_block29; i1++) {
          ctx[`subscription`] = k_block29[i1];
          ctx[`subscription_index`] = i1;
          const key1 = ctx['subscription_index'];
          c_block29[i1] = withKey(comp4({object: ctx['subscription'].target}, key + `__4__${key1}`, node, this, null), key1);
        }
        ctx = ctx.__proto__;
        const b29 = list(c_block29);
        b28 = block28([], [b29]);
      }
      b27 = block27([hdlr13, attr3, hdlr14], [b28]);
    }
    if (ctx['store'].activeComponent.instance.children.length>0) {
      let b32, b35;
      const v14 = ctx['this'];
      let hdlr15 = ["stop", (_ev)=>v14.toggleCategory(_ev,'instance'), ctx];
      let attr4 = {'fa-caret-right':!ctx['store'].activeComponent.instance.toggled,'fa-caret-down':ctx['store'].activeComponent.instance.toggled};
      if (ctx['store'].activeComponent.path.length>1) {
        const v15 = ctx['this'];
        let hdlr16 = ["stop", ()=>v15.store.inspectComponent('compiled template'), ctx];
        const b33 = block33([hdlr16]);
        const v16 = ctx['this'];
        let hdlr17 = ["stop", ()=>v16.store.inspectComponent('raw template'), ctx];
        const b34 = block34([hdlr17]);
        b32 = multi([b33, b34]);
      }
      ctx = Object.create(ctx);
      const [k_block35, v_block35, l_block35, c_block35] = prepareList(ctx['store'].activeComponent.instance.children);;
      for (let i1 = 0; i1 < l_block35; i1++) {
        ctx[`instance`] = k_block35[i1];
        ctx[`instance_index`] = i1;
        const key1 = ctx['instance_index'];
        let b37;
        if (ctx['store'].activeComponent.instance.toggled) {
          b37 = comp5({object: ctx['instance']}, key + `__5__${key1}`, node, this, null);
        }
        c_block35[i1] = withKey(multi([b37]), key1);
      }
      ctx = ctx.__proto__;
      b35 = list(c_block35);
      b31 = block31([hdlr15, attr4], [b32, b35]);
    }
    if (ctx['store'].activeComponent.hooks?.children.length>0) {
      const v17 = ctx['this'];
      let hdlr18 = ["stop", (_ev)=>v17.toggleCategory(_ev,'hooks'), ctx];
      let attr5 = {'fa-caret-right':!ctx['store'].activeComponent.hooks.toggled,'fa-caret-down':ctx['store'].activeComponent.hooks.toggled};
      const v18 = ctx['this'];
      let hdlr19 = ["stop", ()=>v18.store.removeBreakpoints(), ctx];
      ctx = Object.create(ctx);
      const [k_block39, v_block39, l_block39, c_block39] = prepareList(ctx['store'].activeComponent.hooks.children);;
      for (let i1 = 0; i1 < l_block39; i1++) {
        ctx[`hook`] = k_block39[i1];
        ctx[`hook_index`] = i1;
        const key1 = ctx['hook_index'];
        let b41;
        if (ctx['store'].activeComponent.hooks.toggled) {
          b41 = comp6({object: ctx['hook']}, key + `__6__${key1}`, node, this, null);
        }
        c_block39[i1] = withKey(multi([b41]), key1);
      }
      ctx = ctx.__proto__;
      const b39 = list(c_block39);
      b38 = block38([hdlr18, attr5, hdlr19], [b39]);
    }
    const b14 = block14([], [b15, b19, b23, b27, b31, b38]);
    return multi([b2, b14]);
  }
},

"devtools.ObjectTreeElement": function devtools_ObjectTreeElement(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  const comp1 = app.createComponent(`ObjectTreeElement`, true, false, false, ["object","class"]);
  
  let block2 = createBlock(`<div class="m-0 p-0 text-nowrap w-100 object-line" block-attribute-0="class" block-handler-1="click.stop" block-handler-2="contextmenu.prevent"><div block-attribute-3="style"><i class="fa px-1 pointer-icon caret" block-attribute-4="class" block-attribute-5="style"/><block-text-6/><block-child-0/><block-child-1/><block-child-2/><block-child-3/></div></div>`);
  let block4 = createBlock(`<span class="getter-content object-content" block-attribute-0="class" block-handler-1="click.stop"><block-text-2/></span>`);
  let block5 = createBlock(`<span class="object-content" block-attribute-0="class" block-handler-1="dblclick.stop"><block-child-0/><block-child-1/></span>`);
  let block6 = createBlock(`<input block-attribute-0="id" type="text" placeholder="" block-property-1="value" block-handler-2="keydown.stop" block-ref="3"/>`);
  let block8 = createBlock(`<span class="key-changes ms-1 badge p-1" title="Key additions/deletions are observed">+/-</span>`);
  
  return function template(ctx, node, key = "") {
    let b2, b9;
    let b3, b4, b5, b8;
    let attr1 = ctx['props'].class+(ctx['props'].object.hasChildren?' bg-feedback':'');
    const v1 = ctx['this'];
    let hdlr1 = ["stop", ()=>v1.store.toggleObjectTreeElementsDisplay(v1.props.object), ctx];
    let hdlr2 = ["prevent", ctx['openMenu'], ctx];
    let attr2 = `padding-left: ${ctx['objectPadding']}rem`;
    let attr3 = {'fa-caret-right':!ctx['props'].object.toggled,'fa-caret-down':ctx['props'].object.toggled};
    let attr4 = `visibility: ${ctx['props'].object.hasChildren?'':'hidden'};`;
    let txt1 = ctx['props'].object.name;
    if (ctx['props'].object.content.length>0) {
      b3 = text(`: `);
    }
    if (ctx['props'].object.contentType=='getter') {
      let attr5 = ctx['objectLineClass'];
      const v2 = ctx['this'];
      let hdlr3 = ["stop", ()=>v2.store.loadGetterContent(v2.props.object), ctx];
      let txt2 = ctx['props'].object.content;
      b4 = block4([attr5, hdlr3, txt2]);
    } else {
      let b6, b7;
      let attr6 = ctx['objectLineClass'];
      let hdlr4 = ["stop", ctx['setupEditMode'], ctx];
      if (ctx['state'].editMode) {
        let attr7 = `objectEditionInput/${ctx['pathAsString']}`;
        let prop1 = new String((ctx['props'].object.content) === 0 ? 0 : ((ctx['props'].object.content) || ""));
        let hdlr5 = ["stop", ctx['editObject'], ctx];
        let ref1 = (el) => this.__owl__.setRef((`input`), el);
        b6 = block6([attr7, prop1, hdlr5, ref1]);
      } else {
        b7 = text(ctx['props'].object.content);
      }
      b5 = block5([attr6, hdlr4], [b6, b7]);
    }
    if (ctx['keyChanges']) {
      b8 = block8();
    }
    b2 = block2([attr1, hdlr1, hdlr2, attr2, attr3, attr4, txt1], [b3, b4, b5, b8]);
    if (ctx['props'].object.toggled) {
      const tKey_1 = ctx['contextMenuId'];
      ctx = Object.create(ctx);
      const [k_block9, v_block9, l_block9, c_block9] = prepareList(ctx['props'].object.children);;
      for (let i1 = 0; i1 < l_block9; i1++) {
        ctx[`child`] = k_block9[i1];
        ctx[`child_index`] = i1;
        const key1 = ctx['child_index'];
        c_block9[i1] = withKey(comp1({object: ctx['child'],class: ctx['this'].classFor(ctx['child'])}, key + `__1__${key1}`, node, this, null), key1);
      }
      ctx = ctx.__proto__;
      b9 = toggler(tKey_1, list(c_block9));
    }
    return multi([b2, b9]);
  }
},

"utils.HighlightText": function utils_HighlightText(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  
  let block3 = createBlock(`<b block-attribute-0="class"><block-text-1/></b>`);
  
  return function template(ctx, node, key = "") {
    ctx = Object.create(ctx);
    const [k_block1, v_block1, l_block1, c_block1] = prepareList(ctx['splitText']);;
    for (let i1 = 0; i1 < l_block1; i1++) {
      ctx[`name`] = k_block1[i1];
      ctx[`name_index`] = i1;
      const key1 = ctx['name_index'];
      let b3, b4;
      if (ctx['name_index']%2) {
        let attr1 = ctx['constructor'].highlightClass;
        let txt1 = ctx['name'];
        b3 = block3([attr1, txt1]);
      } else {
        b4 = text(ctx['name']);
      }
      c_block1[i1] = withKey(multi([b3, b4]), key1);
    }
    return list(c_block1);
  }
},

"devtools.TreeElement": function devtools_TreeElement(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  const comp1 = app.createComponent(`HighlightText`, true, false, false, ["originalText","searchValue"]);
  const comp2 = app.createComponent(`TreeElement`, true, false, false, ["component"]);
  
  let block2 = createBlock(`<div block-attribute-0="class" class="tree-component m-0 p-0 w-100 text-nowrap user-select-none" block-handler-1="contextmenu.prevent" block-handler-2="mouseover.stop" block-handler-3="click.stop" block-ref="4"><div class="component-wrapper" block-attribute-5="style"><i class="fa px-1 pointer-icon caret" block-attribute-6="class" block-attribute-7="style" block-handler-8="click.stop"/><block-child-0/><span style="color: var(--component-color);"><block-child-1/><block-child-2/></span><block-child-3/><block-child-4/></div></div>`);
  let block3 = createBlock(`<span>&lt;</span>`);
  let block6 = createBlock(`<span style="color: var(--key-name);"> key</span>`);
  let block8 = createBlock(`<span style="color: var(--key-content);"><block-text-0/></span>`);
  let block9 = createBlock(`<span>&gt;</span>`);
  let block10 = createBlock(`<span class="version">owl=<block-text-0/></span>`);
  
  return function template(ctx, node, key = "") {
    let b2, b11;
    let b3, b4, b5, b9, b10;
    let attr1 = {'component-selected':ctx['props'].component.selected,'component-highlighted':ctx['props'].component.highlighted};
    let hdlr1 = ["prevent", ctx['openMenu'], ctx];
    const v1 = ctx['this'];
    const v2 = ctx['props'];
    let hdlr2 = ["stop", ()=>v1.store.highlightComponent(v2.component.path), ctx];
    let hdlr3 = ["stop", ctx['toggleComponent'], ctx];
    let ref1 = (el) => this.__owl__.setRef((`element`), el);
    let attr2 = `padding-left: ${ctx['componentPadding']}rem`;
    let attr3 = {'fa-caret-right':!ctx['props'].component.toggled,'fa-caret-down':ctx['props'].component.toggled};
    let attr4 = (ctx['props'].component.children.length>0?'':'visibility: hidden;');
    let hdlr4 = ["stop", ctx['toggleDisplay'], ctx];
    if (ctx['props'].component.depth) {
      b3 = block3();
    }
    b4 = comp1({originalText: ctx['props'].component.name,searchValue: ctx['state'].searched?ctx['store'].componentSearch.search:''}, key + `__1`, node, this, null);
    if (ctx['minimizedKey'].length>0) {
      let b6, b7, b8;
      if (ctx['minimizedKey'].length>0) {
        b6 = block6();
      }
      b7 = text(`=`);
      let txt1 = ctx['minimizedKey'];
      b8 = block8([txt1]);
      b5 = multi([b6, b7, b8]);
    }
    if (ctx['props'].component.depth) {
      b9 = block9();
    } else {
      let txt2 = ctx['props'].component.version;
      b10 = block10([txt2]);
    }
    b2 = block2([attr1, hdlr1, hdlr2, hdlr3, ref1, attr2, attr3, attr4, hdlr4], [b3, b4, b5, b9, b10]);
    if (ctx['props'].component.toggled) {
      ctx = Object.create(ctx);
      const [k_block11, v_block11, l_block11, c_block11] = prepareList(ctx['props'].component.children);;
      for (let i1 = 0; i1 < l_block11; i1++) {
        ctx[`child`] = k_block11[i1];
        ctx[`child_value`] = v_block11[i1];
        const key1 = ctx['child'].key;
        c_block11[i1] = withKey(comp2({component: ctx['child_value']}, key + `__2__${key1}`, node, this, null), key1);
      }
      ctx = ctx.__proto__;
      b11 = list(c_block11);
    }
    return multi([b2, b11]);
  }
},

"devtools.DevtoolsWindow": function devtools_DevtoolsWindow(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  const comp1 = app.createComponent(`Tab`, true, false, false, ["tabName"]);
  const comp2 = app.createComponent(`Tab`, true, false, false, ["tabName"]);
  const comp3 = app.createComponent(`ComponentsTab`, true, false, false, []);
  const comp4 = app.createComponent(`ProfilerTab`, true, false, false, []);
  const comp5 = app.createComponent(`ContextMenu`, true, false, false, ["items"]);
  
  let block1 = createBlock(`<div id="container" class="d-flex w-100 h-100 flex-column position-absolute overflow-hidden" block-handler-0="mouseover.stop" block-handler-1="mouseout.stop"><block-child-0/><block-child-1/><block-child-2/><block-child-3/></div>`);
  let block2 = createBlock(`<div class="status-message d-flex justify-content-center align-items-center"> Extension context is invalid. Please close the devtools and reload the page. </div>`);
  let block4 = createBlock(`<div class="panel-top d-flex align-items-center custom-navbar"><block-child-0/><block-child-1/><block-child-2/><i class="ms-auto p-1 me-1 lg-icon fa fa-question-circle navbar-icon" title="Open devtools doc" block-handler-0="click.stop"/><i class="p-1 me-1 lg-icon fa navbar-icon" title="Toggle dark mode" block-attribute-1="class" block-handler-2="click.stop"/><i class="p-1 me-1 lg-icon fa fa-repeat navbar-icon" title="Refresh extension" block-handler-3="click.stop"/></div>`);
  let block7 = createBlock(`<select class="form-select form-select-sm custom-select navbar-select border-0" block-handler-0="change"><block-child-0/></select>`);
  let block9 = createBlock(`<option block-attribute-0="value"><block-text-1/></option>`);
  let block12 = createBlock(`<div class="status-message d-flex justify-content-center align-items-center"> Owl is not loaded on this page. </div>`);
  
  return function template(ctx, node, key = "") {
    let b2, b3, b12, b13;
    const v1 = ctx['this'];
    let hdlr1 = ["stop", ()=>v1.store.removeHighlights(), ctx];
    const v2 = ctx['this'];
    let hdlr2 = ["stop", ()=>v2.store.removeHighlights(), ctx];
    if (!ctx['store'].extensionContextStatus) {
      b2 = block2();
    } else if (ctx['store'].owlStatus) {
      let b4, b10, b11;
      let b5, b6, b7;
      b5 = comp1({tabName: 'ComponentsTab'}, key + `__1`, node, this, null);
      b6 = comp2({tabName: 'ProfilerTab'}, key + `__2`, node, this, null);
      if (ctx['store'].frameUrls.length>1) {
        let hdlr3 = [ctx['selectFrame'], ctx];
        ctx = Object.create(ctx);
        const [k_block8, v_block8, l_block8, c_block8] = prepareList(ctx['store'].frameUrls);;
        for (let i1 = 0; i1 < l_block8; i1++) {
          ctx[`frame`] = k_block8[i1];
          ctx[`frame_index`] = i1;
          const key1 = ctx['frame_index'];
          let attr1 = ctx['frame'];
          let txt1 = ctx['frame'];
          c_block8[i1] = withKey(block9([attr1, txt1]), key1);
        }
        ctx = ctx.__proto__;
        const b8 = list(c_block8);
        b7 = block7([hdlr3], [b8]);
      }
      const v3 = ctx['this'];
      let hdlr4 = ["stop", ()=>v3.store.openDocumentation(), ctx];
      let attr2 = {'fa-sun-o':ctx['store'].settings.darkMode,'fa-moon-o':!ctx['store'].settings.darkMode};
      const v4 = ctx['this'];
      let hdlr5 = ["stop", ()=>v4.store.toggleDarkMode(), ctx];
      const v5 = ctx['this'];
      let hdlr6 = ["stop", ()=>v5.store.refreshExtension(), ctx];
      b4 = block4([hdlr4, attr2, hdlr5, hdlr6], [b5, b6, b7]);
      if (ctx['store'].page==='ComponentsTab') {
        b10 = comp3({}, key + `__3`, node, this, null);
      }
      if (ctx['store'].page==='ProfilerTab') {
        b11 = comp4({}, key + `__4`, node, this, null);
      }
      b3 = multi([b4, b10, b11]);
    } else {
      b12 = block12();
    }
    if (ctx['store'].contextMenu) {
      b13 = comp5({items: ctx['store'].contextMenu.items}, key + `__5`, node, this, null);
    }
    return block1([hdlr1, hdlr2], [b2, b3, b12, b13]);
  }
},

"devtools.Event": function devtools_Event(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  
  let block1 = createBlock(`<div class="event-container" block-attribute-0="class"><div class="my-0 p-0 object-line" block-handler-1="click.stop"><div class="ps-2 text-nowrap"><i class="fa px-1 pointer-icon caret" block-attribute-2="class" block-attribute-3="style"/><block-text-4/>: &lt;<span style="cursor:pointer; color: var(--component-color);" block-handler-5="click.stop" block-handler-6="mouseover.stop" block-handler-7="contextmenu"><block-text-8/></span><block-child-0/>&gt; <span> (<block-text-9/>ms) </span></div></div><block-child-1/></div>`);
  let block3 = createBlock(`<span style="color: var(--key-name);"> key</span>`);
  let block5 = createBlock(`<span style="color: var(--key-content);"><block-text-0/></span>`);
  let block6 = createBlock(`<div class="my-0 pt-1 object-line"><i class="fa fa-caret-right mx-1 pe-2" style="visibility: hidden;"/><span> origin: &lt;<span style="cursor:pointer; color: var(--component-color);" block-handler-0="click.stop" block-handler-1="mouseover.stop"><block-text-2/></span><block-child-0/>&gt; </span></div>`);
  let block8 = createBlock(`<span style="color: var(--key-name);"> key</span>`);
  let block10 = createBlock(`<span style="color: var(--key-content);"><block-text-0/></span>`);
  
  return function template(ctx, node, key = "") {
    let b2, b6;
    let attr1 = {'event-last':ctx['props'].event.isLast};
    let hdlr1 = ["stop", ctx['toggleDisplay'], ctx];
    let attr2 = {'fa-caret-right':!ctx['props'].event.toggled,'fa-caret-down':ctx['props'].event.toggled};
    let attr3 = `visibility: ${ctx['props'].event.origin?'':'hidden'};`;
    let txt1 = ctx['props'].event.type;
    const v1 = ctx['this'];
    const v2 = ctx['props'];
    let hdlr2 = ["stop", ()=>v1.store.selectComponent(v2.event.path), ctx];
    const v3 = ctx['this'];
    const v4 = ctx['props'];
    let hdlr3 = ["stop", ()=>v3.store.highlightComponent(v4.event.path), ctx];
    let hdlr4 = [ctx['openMenu'], ctx];
    let txt2 = ctx['props'].event.component;
    if (ctx['minimizedKey'].length>0) {
      let b3, b4, b5;
      if (ctx['minimizedKey'].length>0) {
        b3 = block3();
      }
      b4 = text(`=`);
      let txt3 = ctx['minimizedKey'];
      b5 = block5([txt3]);
      b2 = multi([b3, b4, b5]);
    }
    let txt4 = ctx['renderTime'];
    if (ctx['props'].event.toggled) {
      let b7;
      const v5 = ctx['this'];
      const v6 = ctx['props'];
      let hdlr5 = ["stop", ()=>v5.store.selectComponent(v6.event.origin.path), ctx];
      const v7 = ctx['this'];
      const v8 = ctx['props'];
      let hdlr6 = ["stop", ()=>v7.store.highlightComponent(v8.event.origin.path), ctx];
      let txt5 = ctx['props'].event.origin.component;
      if (ctx['originMinimizedKey'].length>0) {
        const b8 = block8();
        const b9 = text(`=`);
        let txt6 = ctx['originMinimizedKey'];
        const b10 = block10([txt6]);
        b7 = multi([b8, b9, b10]);
      }
      b6 = block6([hdlr5, hdlr6, txt5], [b7]);
    }
    return block1([attr1, hdlr1, attr2, attr3, txt1, hdlr2, hdlr3, hdlr4, txt2, txt4], [b2, b6]);
  }
},

"devtools.EventNode": function devtools_EventNode(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  const comp1 = app.createComponent(`EventNode`, true, false, false, ["event"]);
  
  let block2 = createBlock(`<div class="my-0 p-0 object-line" block-handler-0="click.stop" block-handler-1="contextmenu"><div class="text-nowrap" block-attribute-2="style"><i class="fa px-1 pointer-icon caret" block-attribute-3="class" block-attribute-4="style"/><span><block-text-5/>: &lt;<span style="cursor:pointer; color: var(--component-color);" block-handler-6="click.stop" block-handler-7="mouseover.stop" block-handler-8="contextmenu.stop"><block-text-9/></span><block-child-0/>&gt; <span> (<block-text-10/>ms) </span></span></div></div>`);
  let block4 = createBlock(`<span style="color: var(--key-name);"> key</span>`);
  let block6 = createBlock(`<span style="color: var(--key-content);"><block-text-0/></span>`);
  
  return function template(ctx, node, key = "") {
    let b2, b7;
    let b3;
    let hdlr1 = ["stop", ctx['toggleDisplay'], ctx];
    let hdlr2 = [ctx['openNodeMenu'], ctx];
    let attr1 = `padding-left: ${ctx['eventPadding']}rem`;
    let attr2 = {'fa-caret-right':!ctx['props'].event.toggled,'fa-caret-down':ctx['props'].event.toggled};
    let attr3 = `visibility: ${ctx['props'].event.children.length>0?'':'hidden'};`;
    let txt1 = ctx['props'].event.type;
    const v1 = ctx['this'];
    const v2 = ctx['props'];
    let hdlr3 = ["stop", ()=>v1.store.selectComponent(v2.event.path), ctx];
    const v3 = ctx['this'];
    const v4 = ctx['props'];
    let hdlr4 = ["stop", ()=>v3.store.highlightComponent(v4.event.path), ctx];
    let hdlr5 = ["stop", ctx['openComponentMenu'], ctx];
    let txt2 = ctx['props'].event.component;
    if (ctx['minimizedKey'].length>0) {
      let b4, b5, b6;
      if (ctx['minimizedKey'].length>0) {
        b4 = block4();
      }
      b5 = text(`=`);
      let txt3 = ctx['minimizedKey'];
      b6 = block6([txt3]);
      b3 = multi([b4, b5, b6]);
    }
    let txt4 = ctx['renderTime'];
    b2 = block2([hdlr1, hdlr2, attr1, attr2, attr3, txt1, hdlr3, hdlr4, hdlr5, txt2, txt4], [b3]);
    if (ctx['props'].event.toggled) {
      ctx = Object.create(ctx);
      const [k_block7, v_block7, l_block7, c_block7] = prepareList(ctx['props'].event.children);;
      for (let i1 = 0; i1 < l_block7; i1++) {
        ctx[`child`] = k_block7[i1];
        const key1 = ctx['child'].id;
        c_block7[i1] = withKey(comp1({event: ctx['child']}, key + `__1__${key1}`, node, this, null), key1);
      }
      ctx = ctx.__proto__;
      b7 = list(c_block7);
    }
    return multi([b2, b7]);
  }
},

"devtools.EventSearchBar": function devtools_EventSearchBar(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  
  let block1 = createBlock(`<div class="search-bar-wrapper"><i class="fa fa-search search-icon" aria-hidden="true"/><input type="text" class="search-input" placeholder="Search" block-property-0="value" block-handler-1="keyup.stop"/><block-child-0/></div>`);
  let block2 = createBlock(`<i class="fa fa-times lg-icon utility-icon pe-2" block-handler-0="click.stop"/>`);
  
  return function template(ctx, node, key = "") {
    let b2;
    let prop1 = new String((ctx['store'].eventSearch.search) === 0 ? 0 : ((ctx['store'].eventSearch.search) || ""));
    let hdlr1 = ["stop", ctx['updateSearch'], ctx];
    if (ctx['store'].eventSearch.search.length>0) {
      let hdlr2 = ["stop", ctx['clearSearch'], ctx];
      b2 = block2([hdlr2]);
    }
    return block1([prop1, hdlr1], [b2]);
  }
},

"devtools.ProfilerTab": function devtools_ProfilerTab(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  let { prepareList, withKey } = helpers;
  const comp1 = app.createComponent(`EventNode`, true, false, false, ["event"]);
  const comp2 = app.createComponent(`Event`, true, false, false, ["event"]);
  
  let block1 = createBlock(`<div class="position-relative overflow-hidden d-flex flex-column h-100"><div class="panel-top d-flex align-items-center"><i title="Start/Stop Recording" class="fa fa-circle profiler-icon p-2" block-attribute-0="style" aria-hidden="true" block-handler-1="click.stop"/><i title="Clear events" class="fa fa-ban profiler-icon p-2" aria-hidden="true" block-handler-2="click.stop"/><div class="icons-separator"/><select class="form-select form-select-sm custom-select pointer-icon border-0" block-handler-3="change"><option block-property-4="selected" value="Tree">Tree view</option><option block-property-5="selected" value="List">Events log</option></select><i title="Collapse All" class="fa fa-list p-2 profiler-icon" block-attribute-6="style" block-handler-7="click"/><div class="icons-separator"/><label class="p-1 mx-1 form-check-label pointer-icon" title="Trace renderings in console"><input type="checkbox" class="form-check-input me-1 pointer-icon" block-property-8="checked" block-handler-9="input"/> Trace Renderings </label><label class="p-1 mx-1 form-check-label pointer-icon" title="Trace subscriptions in console (warning: it is VERY verbose)"><input type="checkbox" class="form-check-input me-1 pointer-icon" block-property-10="checked" block-handler-11="input"/> Trace Subscriptions </label><!-- <EventSearchBar/> --></div><div class="events-container h-100 font-monospace"><block-child-0/><block-child-1/></div></div>`);
  let block2 = createBlock(`<div class="status-message d-flex justify-content-center align-items-center"><div> Click on the <i class="fa fa-circle" style="font-size: 0.8em;"/> button to start recording events. </div></div>`);
  
  return function template(ctx, node, key = "") {
    let b2, b3;
    let attr1 = `color: ${ctx['store'].activeRecorder?'var(--active-recorder)':'var(--text-color)'};`;
    const v1 = ctx['this'];
    let hdlr1 = ["stop", ()=>v1.store.toggleRecording(), ctx];
    const v2 = ctx['this'];
    let hdlr2 = ["stop", ()=>v2.store.clearEventsConsole(), ctx];
    let hdlr3 = [ctx['selectDisplayMode'], ctx];
    let prop1 = new Boolean(ctx['store'].eventsTreeView);
    let prop2 = new Boolean(!ctx['store'].eventsTreeView);
    let attr2 = (ctx['store'].eventsTreeView?'':'display: none;');
    const v3 = ctx['this'];
    let hdlr4 = [()=>v3.store.collapseAll(), ctx];
    let prop3 = new Boolean(ctx['store'].traceRenderings);
    const v4 = ctx['this'];
    let hdlr5 = [()=>v4.store.toggleTracing(), ctx];
    let prop4 = new Boolean(ctx['store'].traceSubscriptions);
    const v5 = ctx['this'];
    let hdlr6 = [()=>v5.store.toggleSubscriptionTracing(), ctx];
    if (ctx['showHelp']()) {
      b2 = block2();
    } else {
      let b4, b6;
      if (ctx['store'].eventsTreeView) {
        ctx = Object.create(ctx);
        const [k_block4, v_block4, l_block4, c_block4] = prepareList(ctx['store'].eventsTree);;
        for (let i1 = 0; i1 < l_block4; i1++) {
          ctx[`event`] = k_block4[i1];
          const key1 = ctx['event'].id;
          c_block4[i1] = withKey(comp1({event: ctx['event']}, key + `__1__${key1}`, node, this, null), key1);
        }
        ctx = ctx.__proto__;
        b4 = list(c_block4);
      } else {
        ctx = Object.create(ctx);
        const [k_block6, v_block6, l_block6, c_block6] = prepareList(ctx['store'].events);;
        for (let i1 = 0; i1 < l_block6; i1++) {
          ctx[`event`] = k_block6[i1];
          ctx[`event_index`] = i1;
          const key1 = ctx['event_index'];
          c_block6[i1] = withKey(comp2({event: ctx['event']}, key + `__2__${key1}`, node, this, null), key1);
        }
        ctx = ctx.__proto__;
        b6 = list(c_block6);
      }
      b3 = multi([b4, b6]);
    }
    return block1([attr1, hdlr1, hdlr2, hdlr3, prop1, prop2, attr2, hdlr4, prop3, hdlr5, prop4, hdlr6], [b2, b3]);
  }
},

"devtools.Tab": function devtools_Tab(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  
  let block1 = createBlock(`<div class="navbar-btn d-block" block-attribute-0="class" block-handler-1="click"><block-text-2/></div>`);
  
  return function template(ctx, node, key = "") {
    let attr1 = ctx['active']?'btn-selected':'';
    let hdlr1 = [ctx['selectTab'], ctx];
    let txt1 = ctx['name'];
    return block1([attr1, hdlr1, txt1]);
  }
},

"popup.PopUpApp": function popup_PopUpApp(app, bdom, helpers
) {
  let { text, createBlock, list, multi, html, toggler, comment } = bdom;
  
  let block1 = createBlock(`<div class="container m-0 p-4 text-white bg-dark" style="width: 370px"><block-child-0/><block-child-1/><block-child-2/></div>`);
  let block2 = createBlock(`<p> Owl is detected on this page but the version seems to be outdated. Please upgrade to a newer version in order to use the devtools. </p>`);
  let block3 = createBlock(`<p> Owl is detected on this page. Open DevTools and look for the Owl panel. </p>`);
  let block4 = createBlock(`<p> Owl is not detected on this page. </p>`);
  
  return function template(ctx, node, key = "") {
    let b2, b3, b4;
    if (ctx['state'].status===1) {
      b2 = block2();
    } else if (ctx['state'].status===2) {
      b3 = block3();
    } else {
      b4 = block4();
    }
    return block1([], [b2, b3, b4]);
  }
},
 
}