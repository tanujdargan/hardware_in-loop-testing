# hil_tester_cli/output_checker.py
import json
import re

def compare_json_structures(received_obj, expected_obj, path="root"):
    """
    Recursively compares a received Python object (from parsed JSON) against an
    expected Python object (from parsed expected_values JSON which includes validation rules).
    Returns a list of discrepancies (strings).
    """
    discrepancies = []

    if isinstance(expected_obj, dict) and isinstance(received_obj, dict):
        # Check for missing keys in received that are expected (unless ANY_OR_MISSING)
        for key, exp_val in expected_obj.items():
            current_path = f"{path}.{key}"
            if key not in received_obj:
                if isinstance(exp_val, str) and exp_val == "ANY_OR_MISSING":
                    # It's okay if it's missing
                    pass
                elif isinstance(exp_val, dict) and exp_val.get("$optional") is True:
                    pass # Also okay if marked as optional
                else:
                    discrepancies.append(f"Missing key '{current_path}' in received data.")
            else: # Key exists, compare values
                rec_val = received_obj[key]
                discrepancies.extend(compare_json_structures(rec_val, exp_val, current_path))
        
        # Optional: Check for extra keys in received that were not expected
        # for key in received_obj:
        #     if key not in expected_obj:
        #         discrepancies.append(f"Extra key '{path}.{key}' found in received data.")

    elif isinstance(expected_obj, list) and isinstance(received_obj, list):
        # Basic list comparison: must have same length and elements must match in order
        # More complex array matching rules (array_contains_all, array_each_matches_ordered)
        # would be handled if `expected_obj` was a dict like `{"type": "array_contains_all", ...}`
        if len(received_obj) != len(expected_obj):
            discrepancies.append(f"Array length mismatch at '{path}'. Expected {len(expected_obj)}, Got {len(received_obj)}.")
        else:
            for i, (rec_item, exp_item) in enumerate(zip(received_obj, expected_obj)):
                discrepancies.extend(compare_json_structures(rec_item, exp_item, f"{path}[{i}]"))

    elif isinstance(expected_obj, str): # Special validation string
        # Handle special string validators like "TYPE:string", "REGEX:pattern", etc.
        if expected_obj == "ANY":
            pass # Matches anything, no discrepancy
        elif expected_obj == "ANY_OR_MISSING": # Already handled by key check
            pass
        elif expected_obj.startswith("TYPE:"):
            type_name = expected_obj.split(":", 1)[1]
            type_map = {"string": str, "number": (int, float), "boolean": bool, "array": list, "object": dict, "null": type(None)}
            if type_name not in type_map:
                discrepancies.append(f"Invalid expected type '{type_name}' at '{path}'.")
            elif not isinstance(received_obj, type_map[type_name]):
                discrepancies.append(f"Type mismatch at '{path}'. Expected {type_name}, Got {type(received_obj).__name__}.")
        elif expected_obj.startswith("REGEX:"):
            pattern = expected_obj.split(":", 1)[1]
            if not isinstance(received_obj, str) or not re.search(pattern, received_obj):
                discrepancies.append(f"Regex mismatch at '{path}'. Value '{received_obj}' does not match pattern '{pattern}'.")
        elif expected_obj.startswith("VALUE_GT:"):
            try:
                num = float(expected_obj.split(":",1)[1])
                if not (isinstance(received_obj, (int,float)) and received_obj > num):
                    discrepancies.append(f"Value at '{path}' ('{received_obj}') not > {num}.")
            except ValueError: discrepancies.append(f"Invalid number for VALUE_GT at '{path}'.")
        elif expected_obj.startswith("VALUE_GTE:"):
            try:
                num = float(expected_obj.split(":",1)[1])
                if not (isinstance(received_obj, (int,float)) and received_obj >= num):
                    discrepancies.append(f"Value at '{path}' ('{received_obj}') not >= {num}.")
            except ValueError: discrepancies.append(f"Invalid number for VALUE_GTE at '{path}'.")
        # ... Implement LT, LTE, CONTAINS, NOT, LENGTH, CHOICE similarly ...
        elif expected_obj.startswith("CHOICE:["):
            try:
                choices_str = expected_obj[len("CHOICE:["):-1] # Remove CHOICE:[]
                # This is a bit naive for parsing a list within a string.
                # A safer way would be `json.loads("[" + choices_str + "]")` if choices_str is proper comma-separated JSON values
                # For simplicity, assuming comma-separated strings, possibly quoted.
                # Example: CHOICE:['red','green','blue'] or CHOICE:[1,2,3]
                # For robust choice parsing, the expected_values_format.md should specify choices as a JSON array.
                # Let's assume for now the spec means choices are actual list in the JSON schema if parsed correctly.
                # This logic path is hit if expected_obj is a *string*. If choices were a list, it'd hit list comparison.
                # This indicates a design flaw in how CHOICE:[...] is defined as a string vs. actual list.
                # For now, this will likely fail unless the expected_values.json defines choice values differently.
                # Revisit: The schema for `CHOICE` should define it as an actual list in the `expected_responses`.
                # The example ` "unit": "CHOICE:['C','F']"` is problematic.
                # It should be ` "unit": { "type": "choice", "values": ["C", "F"] }`
                discrepancies.append(f"CHOICE string validator at '{path}' needs rework in schema and implementation.")

            except Exception as e:
                 discrepancies.append(f"Error parsing CHOICE at '{path}': {e}.")

        else: # Exact literal match
            if received_obj != expected_obj:
                discrepancies.append(f"Value mismatch at '{path}'. Expected '{expected_obj}', Got '{received_obj}'.")
                
    elif isinstance(expected_obj, dict) and "$comment" in expected_obj: # Handle custom dict rules if any
        # E.g. for array item validation: { "type": "array_contains_all", "values": [...] }
        # This part needs more fleshing out based on the array matching rules from the schema doc
        # For now, this is a placeholder
        # discrepancies.append(f"Custom dict rule at '{path}' not fully implemented for comparison.")
        # Fallback to basic dict comparison or type check for now
        if not isinstance(received_obj, type(expected_obj)): # Simplistic check
             discrepancies.append(f"Type mismatch for complex rule at '{path}'. Expected {type(expected_obj).__name__}, Got {type(received_obj).__name__}.")


    else: # Default: Exact literal match for numbers, booleans, null
        if received_obj != expected_obj:
            discrepancies.append(f"Value mismatch at '{path}'. Expected '{expected_obj}', Got '{received_obj}'.")
            
    return discrepancies


def check_output(received_data_obj_or_list_of_lines: any, # Can be parsed JSON (dict/list) or list of lines
                 expected_json_path: str = None,
                 input_data_for_fallback: dict = None): # Fallback not really used with pin emulation
    """
    Checks received data against expected values.
    """
    print("\n--- Output Checking ---")
    
    if not expected_json_path:
        print("Warning: No --expected-values JSON file provided. Meaningful output checking cannot be performed.")
        print("Output Checking Summary: SKIPPED (no expectations defined)")
        return True # Or False if strictness requires expectations

    try:
        with open(expected_json_path, 'r') as f:
            expected_config = json.load(f)
        print(f"Loaded expected values from: {expected_json_path}")
    except FileNotFoundError:
        print(f"Error: Expected values JSON file not found at '{expected_json_path}'.")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode Expected JSON file '{expected_json_path}': {e}")
        return False

    reception_mode = expected_config.get("reception_mode", "lines")
    expected_responses_definition = expected_config.get("expected_responses")

    if expected_responses_definition is None:
        print("Warning: No 'expected_responses' found in the expected values JSON. SKIPPED.")
        return True

    overall_pass = True
    results_log = []

    if reception_mode == "json_object":
        if not isinstance(received_data_obj_or_list_of_lines, dict):
            results_log.append(f"FAIL: Reception mode is 'json_object', but received data is not a parsed dictionary. Received type: {type(received_data_obj_or_list_of_lines)}")
            if isinstance(received_data_obj_or_list_of_lines, dict) and "error" in received_data_obj_or_list_of_lines: # Check if it's our error dict from serial_receiver
                results_log.append(f"  Details: {received_data_obj_or_list_of_lines.get('buffer', 'No buffer info')}")
            overall_pass = False
        else:
            results_log.append("Mode: Comparing received JSON object against expected JSON structure.")
            discrepancies = compare_json_structures(received_data_obj_or_list_of_lines, expected_responses_definition)
            if discrepancies:
                overall_pass = False
                results_log.append("  Discrepancies Found:")
                for d in discrepancies:
                    results_log.append(f"    - {d}")
            else:
                results_log.append("  Received JSON object matches expected structure and values. PASSED.")
    
    elif reception_mode == "lines":
        if not isinstance(received_data_obj_or_list_of_lines, list):
            results_log.append(f"FAIL: Reception mode is 'lines', but received data is not a list of lines. Type: {type(received_data_obj_or_list_of_lines)}")
            overall_pass = False
        else:
            # Use the line-by-line comparison logic (adapted from previous version)
            results_log.append("Mode: Comparing received lines against expected line sequence.")
            expected_line_items = expected_responses_definition
            received_lines = received_data_obj_or_list_of_lines
            
            num_expected = len(expected_line_items)
            num_received = len(received_lines)
            expected_idx = 0
            received_idx = 0

            while expected_idx < num_expected and received_idx < num_received:
                exp_item = expected_line_items[expected_idx]
                curr_rec_line = received_lines[received_idx]
                resp_id = exp_item.get("response_id", f"exp_line_{expected_idx}")
                exp_type = exp_item.get("type")
                log_line = f"  Checking ExpLine[{expected_idx}] ('{resp_id}', Type: {exp_type})"
                match = False

                if exp_type == "exact_line":
                    if curr_rec_line == exp_item.get("value"): match = True
                    log_line += f" vs RecLine[{received_idx}] ('{curr_rec_line}'). Expected: '{exp_item.get('value')}'."
                # ... (add other line types: contains_string, regex_match, ignore_line_count) ...
                else:
                    log_line += " - Unknown line type. FAILED."
                
                if match:
                    log_line += " PASSED."
                    expected_idx += 1
                    received_idx += 1
                else:
                    log_line += " FAILED."
                    overall_pass = False
                    received_idx += 1 # Try next received line against current expected, or implement smarter skip
                results_log.append(log_line)

            if expected_idx < num_expected:
                results_log.append(f"  FAIL: Not all expected lines were matched. Expected {num_expected}, matched {expected_idx}.")
                overall_pass = False
    else:
        results_log.append(f"FAIL: Unknown reception_mode: '{reception_mode}'.")
        overall_pass = False

    print("\nDetailed Check Results:")
    for log in results_log:
        print(log)

    print(f"\nOutput Checking Summary: {'PASSED' if overall_pass else 'FAILED'}")
    return overall_pass 