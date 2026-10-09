#!/usr/bin/env python3
"""Test script to verify the fix for issue #134593"""
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, '/usr/local/lib/hermes-agent')

from model_tools import _select_tool_names
from toolsets import get_all_toolsets, resolve_toolset

def test_case(description, enabled, disabled, expected_has_web_search):
    """Test a specific case and return True if it passes"""
    result = _select_tool_names(enabled, disabled, True)
    actual = 'web_search' in result
    status = "PASS" if actual == expected_has_web_search else "FAIL"
    print(f"{status}: {description}")
    print(f"  Enabled: {enabled}")
    print(f"  Disabled: {disabled}")
    print(f"  Expected web_search: {expected_has_web_search}")
    print(f"  Actual web_search: {actual}")
    if actual != expected_has_web_search:
        # Debug: show what toolsets provide web_search
        web_providers = []
        for ts_name, ts_def in get_all_toolsets().items():
            if ts_name not in ('project', 'desktop_ui', 'catalog'):
                tools_in_ts = resolve_toolset(ts_name)
                if 'web_search' in tools_in_ts:
                    web_providers.append(ts_name)
        print(f"  Web providers: {sorted(web_providers)}")
    print()
    return actual == expected_has_web_search

def main():
    print("Testing fix for issue #134593: web_search should not be disabled when 'search' toolset is disabled but 'web' is enabled")
    print()
    
    all_passed = True
    
    # Test case 1: web enabled, search disabled -> web_search should be AVAILABLE
    all_passed &= test_case(
        "web enabled, search disabled -> web_search should be AVAILABLE",
        ['web'], ['search'], True
    )
    
    # Test case 2: search enabled, web disabled -> web_search should be AVAILABLE (from search)
    all_passed &= test_case(
        "search enabled, web disabled -> web_search should be AVAILABLE",
        ['search'], ['web'], True
    )
    
    # Test case 3: both web and search enabled -> web_search should be AVAILABLE
    all_passed &= test_case(
        "both web and search enabled -> web_search should be AVAILABLE",
        ['web', 'search'], [], True
    )
    
    # Test case 4: neither specified (defaults) -> web_search should be available
    all_passed &= test_case(
        "neither specified -> web_search should be available (defaults)",
        None, None, True
    )
    
    # Test case 5: only search disabled -> web_search should be available (from web by default)
    all_passed &= test_case(
        "only search disabled -> web_search should be available",
        None, ['search'], True
    )
    
    print("=" * 50)
    if all_passed:
        print("ALL TESTS PASSED!")
        return 0
    else:
        print("SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())