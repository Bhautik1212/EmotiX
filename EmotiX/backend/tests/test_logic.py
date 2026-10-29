import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.app.main import band, _hash_password, _verify_password, counsellor_reply, CRISIS

def test_risk_bands():
    assert band(1.0) == "Low"
    assert band(4.0) == "Moderate"
    assert band(7.0) == "High"
    assert band(9.0) == "Critical"

def test_password_hash_is_salted_and_verified():
    a = _hash_password("a-long-test-password")
    b = _hash_password("a-long-test-password")
    assert a != b
    assert _verify_password("a-long-test-password", a)
    assert not _verify_password("wrong-password", a)

def test_crisis_response_contains_india_support():
    message = "I want to end my life"
    assert CRISIS.search(message)
    response = counsellor_reply(message, True)
    assert "112" in response and "14416" in response

def test_non_crisis_fallback_is_supportive():
    reply = counsellor_reply("I feel stressed about exams", False)
    assert "What" in reply or "what" in reply
