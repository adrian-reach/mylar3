import os

import pytest
from mockito import verify

import mylar
from mylar.queues import ddl_cleanup


@pytest.mark.unit
def test_ddl_cleanup(when, monkeypatch):
    monkeypatch.setattr(mylar, "CONFIG", mylar.config.Config("./nothing"))
    monkeypatch.setattr(mylar.CONFIG, "CACHE_DIR", os.getcwd(), raising=False)
    when(os).remove(...)
    ddl_cleanup('1234')
    verify(os, times=1).remove(os.path.join(os.getcwd(), "html_cache", "getcomics-1234.html"))


@pytest.mark.unit
def test_ddl_cleanup_keep_cache(monkeypatch):
    monkeypatch.setattr(mylar, "CONFIG", mylar.config.Config("./nothing"))
    monkeypatch.setattr(mylar.CONFIG, "CACHE_DIR", os.getcwd(), raising=False)
    monkeypatch.setattr(mylar.CONFIG, "KEEP_HTML_CACHE", True, raising=False)
    ddl_cleanup('1234')
    verify(os, times=0).remove(os.path.join(os.getcwd(), "html_cache", "getcomics-1234.html"))

## Queue Functions to mock
# postprocess_main
# search_queue
# worker_main
# nzb_monitor
# cdh_monitor
# queue_inf


def run_search_queue(monkeypatch, item, paused):
    import queue
    import mylar.filers
    import mylar.search
    from mylar.queues import search as search_q

    searched = []
    walked = []

    class FakeFileHandlers:
        def __init__(self, **kwargs):
            walked.append(kwargs)

        def walk_the_walk(self):
            return {'status': False}

    monkeypatch.setattr(mylar, "SEARCHLOCK", False, raising=False)
    monkeypatch.setattr(mylar, "PACK_ISSUEIDS_DONT_QUEUE", {}, raising=False)
    monkeypatch.setattr(mylar.filers, "FileHandlers", FakeFileHandlers)
    monkeypatch.setattr(mylar.search, "searchforissue", lambda issueid, manual=False: searched.append(issueid))
    monkeypatch.setattr(search_q, "series_is_paused", lambda comicid: paused)
    monkeypatch.setattr(search_q.time, "sleep", lambda s: None)

    q = queue.Queue()
    q.put(item)
    q.put('exit')
    search_q.search_queue(q)
    return searched, walked


@pytest.mark.unit
def test_search_queue_skips_paused_series(monkeypatch):
    item = {'comicname': 'King Spawn', 'issuenumber': '1', 'issueid': '882528', 'comicid': '138562'}
    searched, walked = run_search_queue(monkeypatch, item, paused=True)
    assert searched == []
    assert walked == []


@pytest.mark.unit
def test_search_queue_allows_manual_search_on_paused_series(monkeypatch):
    item = {'comicname': 'King Spawn', 'issuenumber': '1', 'issueid': '882528', 'comicid': '138562', 'manual': True}
    searched, walked = run_search_queue(monkeypatch, item, paused=True)
    assert searched == ['882528']


@pytest.mark.unit
def test_search_queue_searches_active_series(monkeypatch):
    item = {'comicname': 'King Spawn', 'issuenumber': '56', 'issueid': '999999', 'comicid': '138562'}
    searched, walked = run_search_queue(monkeypatch, item, paused=False)
    assert searched == ['999999']
