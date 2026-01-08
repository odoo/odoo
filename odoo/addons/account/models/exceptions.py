class TaxClosingNonPostedDependingMovesError(Exception):
    """
        This error contains an action that will be used in the case of a tax closing with branches or tax units where
        the different companies have non-posted closing moves. The action will be a form view if there is only one dependent move
        and a list view if there are more.
    """
    pass
