var visitors = {
    Visitor: require("./visitor"),
    ImportVisitor: require('./import-visitor'),
    ExtendVisitor: require('./extend-visitor'),
    JoinSelectorVisitor: require('./join-selector-visitor'),
    ToCSSVisitor: require('./to-css-visitor')
};

module.exports = visitors;
