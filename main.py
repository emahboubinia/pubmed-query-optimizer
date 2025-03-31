#!/usr/bin/env python3
"""
PubMed Query Optimizer

This tool parses a PubMed search query into nested groups, extracts minimal OR/AND groups,
and then uses Selenium to optimize the query by removing redundant keywords that do not affect
the number of search results. The tool automates a search on PubMed's Advanced Search page,
retrieving the result count before and after keyword removal.

Usage:
    python main.py --query "YOUR_QUERY_HERE"

If no query is provided, a default sample query is used.
"""

import re
import argparse
from typing import List, Union, Tuple, Any
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Type alias for nested query structure.
QueryStructure = Union[str, List[Any]]


# --- Step 1: Query Parsing Functions ---

def tokenize(query: str) -> List[str]:
    """
    Splits the query into tokens, preserving parentheses and logical operators.
    """
    token_pattern = re.compile(r'\(|\)|\bAND\b|\bOR\b|[^\s()]+')
    return token_pattern.findall(query)

def parse_tokens(tokens: List[str]) -> QueryStructure:
    """
    Recursively builds a nested list from the token list.
    """
    tree: List[Any] = []
    while tokens:
        token = tokens.pop(0)
        if token == '(':
            subtree = parse_tokens(tokens)
            tree.append(subtree)
        elif token == ')':
            return tree
        else:
            tree.append(token)
    return tree

def parse_query(query: str) -> QueryStructure:
    """
    Convenience function to tokenize and parse a query.
    """
    tokens = tokenize(query)
    return parse_tokens(tokens)


# --- Step 2: Minimal Group Extraction and Reconstruction ---

def contains_operator(group: QueryStructure) -> bool:
    """
    Checks if the given group contains 'AND' or 'OR'.
    """
    if isinstance(group, list):
        for elem in group:
            if isinstance(elem, list):
                if contains_operator(elem):
                    return True
            elif elem.upper() in ['AND', 'OR']:
                return True
    return False

def get_minimal_operator_groups(tree: QueryStructure) -> List[QueryStructure]:
    """
    Returns the smallest groups (sub-lists) in the query tree that contain logical operators.
    """
    minimal_groups: List[QueryStructure] = []
    if isinstance(tree, list) and contains_operator(tree):
        child_has_operator = False
        for elem in tree:
            if isinstance(elem, list) and contains_operator(elem):
                child_has_operator = True
                minimal_groups.extend(get_minimal_operator_groups(elem))
        if not child_has_operator:
            minimal_groups.append(tree)
    return minimal_groups

def is_list_within(item_list: List[Any]) -> bool:
    """
    Checks if there is any sub-list within the given list.
    """
    return any(isinstance(item, list) for item in item_list)

def join_keyword(item_list: QueryStructure) -> Union[str, List[Any]]:
    """
    Processes the nested query structure to join elements when possible.
    If no "OR" is present and there are no nested lists, it flattens the list into a string.
    """
    modified_list: List[Any] = []
    if isinstance(item_list, list):
        for item in item_list:
            if isinstance(item, list):
                modified_list.append(join_keyword(item))
            else:
                modified_list.append(item)
    else:
        modified_list.append(item_list)
    
    if "OR" not in modified_list and not is_list_within(modified_list):
        return " ".join(modified_list)
    else:
        return modified_list

def reverse_joined_keywords(structure: Union[str, List[Any]], top_level: bool = True) -> str:
    """
    Recursively reconstructs a search query string from the nested structure.
    Each keyword (that is not 'AND' or 'OR') is wrapped in parentheses.
    """
    if isinstance(structure, str):
        if structure.upper() in ["AND", "OR"]:
            return structure
        else:
            return f"({structure})"
    elif isinstance(structure, list):
        reconstructed_parts = [reverse_joined_keywords(item, top_level=False) for item in structure]
        joined_string = " ".join(reconstructed_parts)
        return f"({joined_string})" if not top_level else joined_string


# --- Step 3: Selenium Function to Search and Optimize Query ---

def search_pubmed(query: str, or_keywords: List[List[Union[str, None]]]) -> Tuple[int, str, List[str]]:
    """
    Uses Selenium to search PubMed with the given query and iteratively removes redundant OR keywords.
    
    Args:
      query (str): The search query.
      or_keywords (List[List[Union[str, None]]]): List of OR keywords with position hints.
    
    Returns:
      Tuple containing baseline result count, final search query, and list of excluded keywords.
    """
    driver: WebDriver = webdriver.Chrome()
    try:
        def perform_search(search_q: str) -> int:
            driver.get("https://pubmed.ncbi.nlm.nih.gov/advanced/")
            wait = WebDriverWait(driver, 10)
            query_box = wait.until(EC.presence_of_element_located((By.ID, "query-box-input")))
            query_box.clear()
            query_box.send_keys(search_q)
            search_button = driver.find_element(By.CSS_SELECTOR, "button.search-btn[type='submit']")
            search_button.click()
            result_elem = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.results-amount>h3>span.value")
            ))
            result_text = result_elem.text.strip().replace(',', '')
            return int(result_text)
        
        # Get baseline result count.
        result_count = perform_search(query)
        
        excluded_keywords: List[str] = []
        current_query: str = query
        
        # Iterate over OR keywords and try removal.
        for or_keyword in or_keywords:
            if or_keyword[1] == 'before':
                replace_text = f" OR ({or_keyword[0]})"
            elif or_keyword[1] == 'after':
                replace_text = f"({or_keyword[0]}) OR "
            else:
                replace_text = f"({or_keyword[0]})"
            
            new_query = current_query.replace(replace_text, "")
            new_count = perform_search(new_query)
            if new_count == result_count:
                excluded_keywords.append(or_keyword[0])
                current_query = new_query
        return result_count, current_query, excluded_keywords
    finally:
        driver.quit()

def get_or_keyword(joined_keywords_list: QueryStructure) -> List[List[Union[str, None]]]:
    """
    Extracts OR keywords from the joined keywords structure.
    Returns a list of [keyword, position_hint]. The position hint is set based on order.
    """
    keywords_list: List[List[Union[str, None]]] = []
    if isinstance(joined_keywords_list, list):
        for item in joined_keywords_list:
            if isinstance(item, list):
                keywords_list.extend(get_or_keyword(item))
            else:
                if item.upper() in ["AND", "OR"]:
                    continue
                keywords_list.append([item, None])
    else:
        if joined_keywords_list.upper() not in ["AND", "OR"]:
            keywords_list.append([joined_keywords_list, None])
    
    final_list: List[List[Union[str, None]]] = []
    if keywords_list:
        if len(keywords_list) > 1:
            final_list.append([keywords_list[0][0], "after"])
        else:
            final_list.append([keywords_list[0][0], None])
        for keyword in keywords_list[1:]:
            final_list.append([keyword[0], "before"])
    return final_list


# --- Step 4: Main Function and CLI Interface ---

def main() -> None:
    parser = argparse.ArgumentParser(description="PubMed Query Optimizer")
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="PubMed search query. Enclose in quotes if necessary.",
        default="""
        Gene
        """
    )
    args = parser.parse_args()
    query_str: str = args.query.strip()

    parsed_tree = parse_query(query_str)
    minimal_groups = get_minimal_operator_groups(parsed_tree)
    joined_keywords = join_keyword(minimal_groups)
    search_query = reverse_joined_keywords(joined_keywords)
    or_keyword_list = get_or_keyword(joined_keywords)

    result_num, final_search_query, excluded_keywords = search_pubmed(search_query, or_keyword_list)
    print("\n--- Final Results ---")
    print(f"Result Count: {result_num}")
    print("\nFinal Search Query:")
    print(final_search_query)
    print("\nExcluded Keywords:")
    print("\n".join(excluded_keywords))

if __name__ == "__main__":
    main()