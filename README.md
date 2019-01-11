# SlurpLogin
Generate Selenium IDE Test Cases via a Burpsuite Plugin

### Usage
1. Modify OUTPUT_FILE within the script to where you want to save the file.
2. Save slurp.py
3. Add slurp.py as an extension in Burp
4. Capture a POST request to any domain that sends login information. This can be captured with the proxy or through Repeater.
5. Right click and select Generate Selenium File
6. Open Selenium IDE
7. Load the file at OUTPUT_FILE
8. Run the Test case
