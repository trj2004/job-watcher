from jobwatcher.title_rules import in_role


def test_finance_track_titles_are_in_role():
    assert in_role("Commercial Banking Associate")
    assert in_role("Community Development Loan Officer")
    assert in_role("Financial Planning Associate")
    assert in_role("Real Estate Financial Analyst")


def test_unrelated_titles_are_out_of_role():
    assert not in_role("Branch Operations Manager")
    assert not in_role("Marketing Coordinator")
    assert not in_role("Restaurant General Manager")
