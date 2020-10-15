import scrapy
from urllib.parse import urlencode
import re
import json
from ..items import Product
import logging

API = '0dabb38ed3e0603f8b4f1a354a443476'


def paginate_url(page):
    home_garden_url = f"https://www.amazon.com/s?i=garden&bbn=3295676011&rh=p_36%3A15000-&qid=1602614531&ref=sr_pg_{str(page)}&page={str(page)}"
    return home_garden_url


def get_url(url):
    payload = {'api_key': API, 'url': url, 'country_code': 'us'}
    proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    return proxy_url


class AmazonSpider(scrapy.Spider):
    name = 'amazon_products_with_proxy'
    allowed_domains = ['amazon.com', 'api.scraperapi.com']
    page = 1
    product = Product()

    # def start_requests(self):
    #     url = get_url(home_garden_url)
    #     yield scrapy.Request(url=url, callback=self.parse)

    # Debugging: Product Details Page
    def start_requests(self):
        # sold by amazon = True
        # url = 'https://www.amazon.com/dp/B08J5Y89C7?ref=ods_ucc_kindle_B08J5Y89C7_rc_nd_ucc'
        # sold by amazon = False
        url = 'https://www.amazon.com/BISSELL-Crosswave-Vacuum-Cleaner-2306A/dp/B079WCPPQD/ref=sr_1_23?dchild=1&qid=1602614531&refinements=p_36%3A15000-&s=home-garden&sr=1-23'
        yield scrapy.Request(url=get_url(url), callback=self.parse_product_details)

    def parse(self, response):
        products = response.xpath('//*[@data-component-type="s-search-result"]')
        for product in products:

            is_prime = product.xpath('.//*[@aria-label="Amazon Prime"]')
            logging.info(is_prime)

            if not is_prime:

                asin = product.xpath('@data-asin').extract_first()

                product_url = f"https://www.amazon.com/dp/{asin}"

                meta = {
                    "isPrime": is_prime,
                    "asin": asin,
                    "url": product_url
                }
                yield scrapy.Request(url=get_url(product_url), callback=self.parse_product_details, meta=meta)

        # TODO: enable for production
        # next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
        #
        # if next_page:
        #     logging.info(next_page)
        #     url = f"https://www.amazon.com{next_page}"
        #     logging.info(url)
        #     yield scrapy.Request(url=get_url(url), callback=self.parse)

        # TODO: Disable for production
        if self.page < 4:
            self.page += 1
            url = paginate_url(self.page)
            logging.info(url)
            yield scrapy.Request(url=get_url(url), callback=self.parse)

    def parse_sold_by(self, response):
        self.product['soldBy'] = "someones store"
        yield self.product

    def parse_product_details(self, response):
        # aod-total-offer-count > total number os sellers selector

        def get_asin():
            asin_pattern = re.compile(r"([A-Z0-9]{10})")
            asin_string = response.css("link[rel='canonical']::attr(href)").get()
            asin = asin_pattern.search(asin_string)[0]
            return asin

        def get_sold_by_amazon():
            # get the node
            node = response.css("td .a-truncate.buybox-tabular-content.a-size-small").get()
            # if node
            # remove any extra white space
            if node:
                # check to see if text inside node includes "sold by Amazon.com"
                has_text = "Amazon.com" in node[0].text
                # if True set to "true" if False set to "false"
                if has_text:
                    return "true"
                else:
                    return "false"
            else:
                return "false"

        self.product['asin'] = get_asin()
        self.product['soldByAmazon'] = get_sold_by_amazon()

        if self.product['asin']:
            buying_options_btn = response.css("#buybox-see-all-buying-choices-announce").get()
            if buying_options_btn:
                buying_options_url = get_url(
                    f"https://www.amazon.com/gp/aod/ajax/ref=dp_olp_NEW_mbc?asin={self.product['asin']}")
                yield scrapy.Request(url=buying_options_url, callback=self.parse_sold_by)

        # TODO: reviews int
        #  aboutBullets
        #  totalReviews string
        #  description
        #  sellers
        #  isSellerNameInProductName
        #  inStock
        #  uuid
        #  ean
        #  category
        #  upc
        #  hasBuyBox
        #  isFba