# Expected Output JSON Format (Serial Reception)

This JSON file defines the expected data to be received over serial from the STM32. The received serial data can be a simple text stream or a JSON string.

## Root Object

-   `test_name` (string, optional): Consistency with input JSON.
-   `reception_mode` (string, optional): How to interpret incoming serial data.
    -   `"lines"` (default): Treat incoming data as a sequence of newline-terminated strings. Each item in `expected_responses` will typically match one or more lines.
    -   `"json_object"`: Expect the entire useful response from STM32 (or a significant part of it) to be a single, complete JSON string received over serial. The `expected_responses` will then define how to validate this parsed JSON object.
-   `response_timeout_ms` (integer, optional, default: 10000): Max time to wait for STM32 response.
-   `stop_condition_line` (string, optional): If in `lines` mode, a specific string that signals the end of STM32 output.
-   `expected_responses` (array or object, required):
    -   If `reception_mode` is `"lines"`, this is an **array** of response objects (as in previous versions, for line-by-line matching).
    -   If `reception_mode` is `"json_object"`, this is a **single object** that defines the expected structure and values of the JSON received from STM32.

## Line-by-Line Response Object (for `reception_mode: "lines"`)

Each object in the `expected_responses` array.
-   `response_id` (string, required): Unique ID.
-   `type` (string, required): `exact_line`, `contains_string`, `regex_match`, `ignore_line_count`.
-   `value`/`pattern`/`count`: (As defined previously).
-   `description` (string, optional).

## JSON Object Validation Structure (for `reception_mode: "json_object"`)

The `expected_responses` field becomes a single JSON object that mirrors the expected structure from the STM32.

-   **Keys** in this object must match keys in the received JSON from STM32.
-   **Values** can be:
    -   A literal value for exact match (string, number, boolean, null).
    -   A nested object for matching sub-objects.
    -   An array for matching arrays (see Array Matching below).
    -   A string with special prefixes for advanced validation:
        -   `"ANY"`: The key must exist, its value can be anything (and any type).
        -   `"TYPE:<type_name>"`: Value must be of specified type (e.g., `"TYPE:string"`, `"TYPE:number"`, `"TYPE:boolean"`, `"TYPE:array"`, `"TYPE:object"`).
        -   `"REGEX:<pattern>"`: Value (if string) must match the regex.
        -   `"VALUE_GT:<number>"`: Value must be a number greater than `<number>`.
        -   `"VALUE_GTE:<number>"`: Value must be a number greater than or equal to `<number>`.
        -   `"VALUE_LT:<number>"`: Value must be a number less than `<number>`.
        -   `"VALUE_LTE:<number>"`: Value must be a number less than or equal to `<number>`.
        -   `"CONTAINS:<substring>"`: Value (if string) must contain `<substring>`.
        -   `"NOT:<value>"`: Value must not be equal to `<value>`.
        -   `"LENGTH:<len>"`: For strings or arrays, checks length.
        -   `"CHOICE:[<val1>,<val2>,...]"`: Value must be one of the specified choices (e.g., `"CHOICE:['red','green','blue']"`). Note: JSON strings inside the choice list.

### Array Matching in JSON Object Mode:

If a value in `expected_responses` (JSON object mode) is an array, it can specify:
1.  **Exact array match:** `[1, "two", null]` - received array must be identical.
2.  **Match any array:** Use `"TYPE:array"`.
3.  **Array with specific length:** Use `"LENGTH:<len>"` combined with `"TYPE:array"`.
4.  **Array containing specific items (order doesn't matter, items unique):**
    `{ "key_for_array": { "type": "array_contains_all", "values": ["itemA", "itemB"] } }`
5.  **Array where each item matches a schema (ordered):**
    `{ "key_for_array": { "type": "array_each_matches_ordered", "schemas": [ { "sub_key": "TYPE:string" }, { "sub_key_2": "TYPE:number" } ] } }` (Each element of the received array is validated against the corresponding schema in the `schemas` list).

## Example (Reception Mode: `"json_object"`):

```json
{
  "test_name": "STM32 JSON Output Test",
  "reception_mode": "json_object",
  "response_timeout_ms": 5000,
  "expected_responses": {
    "status": "OK",
    "timestamp": "TYPE:number",
    "data": {
      "sensor_id": "REGEX:^TEMP_\\\\d+$",
      "value": "VALUE_GTE:0",
      "unit": "CHOICE:['C','F']",
      "history": {
        "type": "array_each_matches_ordered",
        "schemas": [
            "TYPE:number", 
            "TYPE:number",
            {"$comment": "Allow up to 5 numbers for history"}
        ],
        "$max_items": 5 
      }
    },
    "error_code": null,
    "optional_field": "ANY_OR_MISSING" 
    // "ANY_OR_MISSING" means if key exists, value can be anything; if key doesn't exist, it's also fine.
    // For a key that must exist and can be anything, use "ANY".
  }
}
```

## Example (Reception Mode: `"lines"`):

```json
{
  "test_name": "STM32 Line Output Test",
  "reception_mode": "lines",
  "stop_condition_line": "TEST_ENDED",
  "expected_responses": [
    { "response_id": "line1", "type": "exact_line", "value": "Booting complete." },
    { "response_id": "line2", "type": "contains_string", "value": "Sensor ID:" }
  ]
}
``` 