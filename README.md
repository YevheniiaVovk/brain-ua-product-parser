# Brain.com.ua Product Parser

Training project: three parsers that collect product data from [brain.com.ua](https://brain.com.ua/)
and save it to PostgreSQL through the Django ORM.

| Parser | Technology | Locators |
|---|---|---|
| Requests / BS4 | `requests`, `beautifulsoup4` | CSS selectors |
| Selenium | `selenium` | XPath only |
| Playwright | `playwright` (async) | XPath only |

## Task

1. Open https://brain.com.ua/
2. Enter the query `Apple iPhone 15 128GB Black` into the search field
3. Click the search button
4. Open the first search result
5. Collect product data
6. Print the collected data
7. Save the result to PostgreSQL and export the table to CSV

## Collected fields

`title`, `color`, `memory`, `manufacturer`, `price`, `sale_price`, `photos` (list of links),
`product_code`, `reviews_count`, `screen_diagonal`, `screen_resolution`,
`specifications` (dict with all characteristics).

Missing values are stored as `None`. Each record has `parser_source`
(`requests_bs4`, `selenium` or `playwright`).

## Tech stack

- Python 3.12, [uv](https://docs.astral.sh/uv/)
- Django + PostgreSQL
- Selenium, Playwright, Requests, BeautifulSoup4

## Project structure

```
parser_project/
├── modules/load_django.py     # Django ORM setup for standalone scripts
├── parser_app/                # Django app (Product model)
├── parser_requests_bs4.py     # Requests / BS4 parser
├── parser_selenium.py         # Selenium parser
├── parser_playwright.py       # Playwright parser
├── docker-compose.yml         # PostgreSQL container
├── .env.example               # Template for local settings
├── pyproject.toml
└── README.md
```

## Setup

```powershell
uv sync
```

1. Create a local `.env` file from the example and fill in real values
   (never commit `.env`):

```powershell
copy .env.example .env
```

2. Start PostgreSQL in Docker:

```powershell
docker compose up -d
```

   The container port `5432` is published on host port `5434` (see `docker-compose.yml`).
   If this port is busy on your machine, change it in `docker-compose.yml`
   and set the same value in `DB_PORT` in `.env`.

3. Apply migrations:

```powershell
python manage.py migrate
```

## Running Selenium and Playwright

Both parsers attach to a Chrome instance that is started manually with a remote debugging port.
Close all Chrome windows, then start Chrome:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome_manual"
```

Keep this window open and run a parser in another terminal:

```powershell
python parser_selenium.py
python parser_playwright.py
```

If the site shows a Cloudflare check, solve it manually in the browser window.
The scripts wait up to 3 minutes for the page.

## Export to CSV

To export all products from the database into a CSV file (products.csv), run:

```
python export_csv.py
```

## Notes

- Selenium and Playwright parsers use XPath only (no BeautifulSoup, no JSON-LD).
- A record is created for every distinct set of values; identical data is not duplicated
- Locators were chosen manually in DevTools and checked with Ctrl+F.
- The site has duplicated blocks (two search fields, hidden product links), so visible elements are selected explicitly.
- If Chrome closes immediately with `DevTools remote debugging is disallowed by the system admin`,
  check `chrome://policy` for the `RemoteDebuggingAllowed` policy.
