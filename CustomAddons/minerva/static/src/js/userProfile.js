function verify(data, type, full) {
    return data == true ?
        Dandelion.actionButton('Taip', 'green verify-remove', full) :
        Dandelion.actionButton('Ne', 'red verify', full);
}