# Step 2: Enter search query into the visible search input
        print('[STEP 2] Entering search query')
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@class='quick-search-input']"))
        )
        search_inputs = driver.find_elements(By.XPATH, "//input[@class='quick-search-input']")
        search_input = next((el for el in search_inputs if el.is_displayed()), None)
        if search_input is None:
            raise NoSuchElementException('Visible search input not found')
        search_input.send_keys('Apple iPhone 15 128GB Black')

        # Debug: what exists on the page after typing (temporary)
        import time
        time.sleep(2)
        for name, xpath in {
            'qsr-submit': "//input[@class='qsr-submit']",
            'qsr-input': "//input[@class='qsr-input']",
            'original button': "//input[@class='search-button-first-form']",
        }.items():
            found = driver.find_elements(By.XPATH, xpath)
            print(f'[DEBUG] {name}: count={len(found)}')
            for el in found:
                print('    displayed=', el.is_displayed(), '| value=', repr(el.get_attribute('value')))

        # Step 3: Click search button of the quick-search popup that opens while typing
        print('[STEP 3] Clicking search button')
        search_button = wait.until(
            lambda d: next(
                (el for el in d.find_elements(By.XPATH, "//input[@class='qsr-submit']") if el.is_displayed()),
                None,
            )
        )
        search_button.click()