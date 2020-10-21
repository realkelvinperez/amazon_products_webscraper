import scrapy
from urllib.parse import urlencode
import re
import json
from amz_snagger_scraper.items import Product
import logging
from unidecode import unidecode
import uuid

API = '0dabb38ed3e0603f8b4f1a354a443476'


def paginate_url(page):
    home_garden_url = f"https://www.amazon.com/s?i=garden&bbn=3295676011&rh=p_36%3A15000-&qid=1602614531&ref=sr_pg_{str(page)}&page={str(page)}"
    return home_garden_url


def get_url(url):
    # payload = {'api_key': API, 'url': url, 'country_code': 'us'}
    # proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    # return proxy_url
    return url


def clean_text(text):
    new_text = " ".join(text.split()).strip()
    remove_unicode = unidecode(new_text)
    if r"\'" in remove_unicode:
        remove_escaped_chars = remove_unicode.replace(r'\'', '')
        return remove_escaped_chars
    else:
        return remove_unicode


class AmazonSpider(scrapy.Spider):
    name = 'amazon_products_with_proxy'
    allowed_domains = ['amazon.com', 'api.scraperapi.com']
    page = 1
    product = Product()
    debug = False
    production = False

    if debug:
        # Debugging: Product Details Page
        def start_requests(self):
            url = 'https://www.amazon.com/dp/B01AXM4WV2'
            yield scrapy.Request(url=get_url(url), callback=self.parse_product_details)
    else:
        # Production
        def start_requests(self):
            url = get_url(paginate_url(self.page))
            yield scrapy.Request(url=url, callback=self.parse)


    def parse(self, response):

        products = response.xpath('//*[@data-component-type="s-search-result"]')

        for product in products:

            is_prime_node = product.xpath('.//*[@aria-label="Amazon Prime"]')
            # logging.info(is_prime_node)

            if not is_prime_node:

                is_prime = 'false'
                asin = product.xpath('@data-asin').extract_first()
                product_url = f"https://www.amazon.com/dp/{asin}"

                meta = {
                    "isPrime": is_prime,
                    "asin": asin,
                    "url": product_url,
                }

                yield scrapy.Request(url=get_url(product_url), callback=self.parse_product_details, meta=meta)



        # TODO: Disable for production

        if self.page and not self.production:
            if self.page < 20:
                self.page += 1
                url = paginate_url(self.page)
                logging.info(url)
                yield scrapy.Request(url=get_url(url), callback=self.parse)
        else:
            pass
            # TODO: enable for production
            # next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
            #
            # if next_page:
            #     logging.info(next_page)
            #     url = f"https://www.amazon.com{next_page}"
            #     logging.info(url)
            #     yield scrapy.Request(url=get_url(url), callback=self.parse)


    def parse_buying_options(self, response):
        def get_sold_by():
            has_see_more_link = response.css("#aod-pinned-offer-show-less-link")
            has_pinned_offer = response.css("#aod-pinned-offer")
            if has_see_more_link and has_pinned_offer:
                return clean_text(response.css(
                    "#aod-pinned-offer-additional-content #aod-offer-soldBy span.a-size-small.a-color-base::text").get())
            else:
                return clean_text(response.css('#aod-offer-soldBy [role="link"]::text').get())
            pass

        def get_seller_name_in_product_name():
            lowercase_title = self.product['title'].lower()
            lowercase_seller_name = self.product['soldBy'].lower()
            seller_name_list = lowercase_seller_name.split()

            if seller_name_list:
                result = None
                for name in seller_name_list:
                    result = name in lowercase_title
                if result:
                    return 'true'
                else:
                    return 'false'
            else:
                return None

        def get_price():

            price_node = response.css(".a-price-whole::text").get()

            if price_node:
                price_text = clean_text(price_node)
                price = float(price_text)
                return price
            else:
                return 0

        def get_seller_store_link():
            sold_by = self.product['soldBy']
            if "Amazon" not in sold_by:
                node = response.css("#aod-pinned-offer-additional-content #aod-offer-soldBy span.a-size-small.a-color-base::attr(href)").get() or \
                       response.css('#aod-offer-soldBy [role="link"]::attr(href)').get()
                clean_node = clean_text(node)
                pattern = re.compile(r'(?:[seller=]|$)([A-Z0-9]{11,15})')
                seller_id = pattern.search(clean_node)[1]
                store_link = f"https://www.amazon.com/s?me={seller_id}&marketplaceID=ATVPDKIKX0DER"

                return store_link
            else:
                return "https://www.Amazon.com"

        if not self.product['soldBy']:
            self.product['soldBy'] = get_sold_by()

        if not self.product['price']:
            self.product['price'] = get_price()

        if not self.product['sellers']:
            # TODO: convert to a functions
            # self.product['sellers'] = get_sellers()
            self.product['sellers'] = int(response.css("#aod-total-offer-count::attr(value)").get())

        self.product['soldByStoreLink'] = get_seller_store_link()
        self.product['isSellerNameInProductName'] = get_seller_name_in_product_name()

        yield self.product

    def parse_product_details(self, response):

        if response.meta and not self.debug:
            # set props to meta values if available
            logging.info('Starting to Harvest >>> ' + response.meta['asin'])
            self.product['asin'] = response.meta['asin']
            self.product['isPrime'] = response.meta['isPrime']
            self.product['url'] = response.meta['url']

        def get_asin():

            asin_string = response.css("link[rel='canonical']::attr(href)").get()
            if asin_string:
                asin_pattern = re.compile(r"dp/([A-Z0-9]{10})")
                asin_result = asin_pattern.search(asin_string)[1]
                return asin_result
            else:
                return None

        def get_sold_by_amazon():

            node = response.css("td .a-truncate.buybox-tabular-content.a-size-small").get()
            if node:
                has_text = "Amazon.com" in node
                if has_text:
                    return "true"
                else:
                    return "false"
            else:
                return "false"

        def get_bsr():

            bsr_selectors = [
                '#productDetails_detailBullets_sections1',
                '#productDetails_db_sections',
                'div#detailBulletsWrapper_feature_div'
            ]

            for selector in bsr_selectors:
                # loop through all of the selector to see which one is true
                product_info_node = response.css(selector).get()

                if product_info_node:
                    bsr_pattern = re.compile(r"#(\d*,?\d*,?\d*)\sin")
                    matches = bsr_pattern.findall(product_info_node)
                    if matches:
                        bsr_text = matches[0].replace(",", '')
                        bsr = int(bsr_text)
                        return bsr
                    else:
                        continue
                else:
                    continue

            return 0

        def get_fba():

            fba_node = response.css("#buyboxTabularTruncate-0 span::text").get()

            if fba_node:
                has_fba = "Amazon" in fba_node

                if has_fba:
                    return "true"
                else:
                    return "false"
            else:
                return "false"

        def get_about_bullets():

            about_bullets = response.xpath("//*[@id='feature-bullets']/ul/li")

            if about_bullets:

                all_about_bullets = []

                for bullet in about_bullets:
                    bullet_text = bullet.xpath('.//span/text()').get()
                    single_bullet = clean_text(bullet_text)
                    if single_bullet == '':
                        continue
                    else:
                        all_about_bullets.append(single_bullet)

                return all_about_bullets
            else:
                return []

        def get_description():

            description_selectors = [
               '#productDescription_feature_div p::text',
               '#productDescription_feature_div p span::text'
            ]

            for selector in description_selectors:
                description_node = response.css(selector).get()

                if description_node:
                    return clean_text(description_node)
                else:
                    continue

            return ""

        def get_title():
            title_text = response.css("#productTitle::text").get()
            title = clean_text(title_text)
            return title

        def get_buy_box():

            buy_box_node = response.css("#add-to-cart-button").get() or \
                           response.css("#usedbuyBox div.a-button-stack").get()

            if buy_box_node:
                return 'true'
            else:
                return 'false'

        def get_rating():

            rating_node = response.css("#acrPopover").get()

            if rating_node:
                rating_pattern = re.compile(r'(\d+\.\d+|\d+)')
                rating_text = rating_pattern.search(rating_node)
                rating = float(rating_text[0])
                return rating
            else:
                return 0

        def get_sold_by():

            sold_by_selectors = [
                "#buyboxTabularTruncate-1 span a::text",
                "#buyboxTabularTruncate-1 span::text",
                "#buyboxTabularTruncate-1 span.a-truncate-full::text",
                "#buyboxTabularTruncate-1 span.a-truncate-cut::text",
                "a#sellerProfileTriggerId::text"
            ]

            for selector in sold_by_selectors:
                sold_by_node = response.css(selector).get()
                if sold_by_node:
                    sold_by = clean_text(sold_by_node)
                    return sold_by

            return ""

        def get_sellers():

            sellers_node = response.css("#olp-upd-new-used a span:nth-child(1)::text").get()

            if sellers_node:
                sellers_text = clean_text(sellers_node)
                sellers_pattern = re.compile(r"\((\d+)\)")
                sellers_match = sellers_pattern.search(sellers_text)[1]
                sellers = int(sellers_match)
                return sellers
            else:
                return 0

        def get_price():

            price_node = response.css("#priceblock_ourprice::text").get()

            if price_node:
                price_pattern = re.compile(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})")
                price_text = clean_text(price_node)
                price_match = price_pattern.search(price_text)[0]
                price = float(price_match)
                return price
            else:
                return 0

        def get_total_reviews():
            total_reviews_node = response.css('#averageCustomerReviews_feature_div #acrCustomerReviewText::text').get()
            if total_reviews_node:
                total_reviews_pattern = re.compile(r"\d{1,3}(?:[,]\d{3})*")
                total_reviews_match = total_reviews_pattern.search(total_reviews_node)[0]
                clean_total_reviews = "".join(total_reviews_match.split(','))
                total_reviews = int(clean_total_reviews)
                return total_reviews
            else:
                return 0

        def get_image():

            image_node = clean_text(response.css("#imageBlock_feature_div > script::text").get())

            if image_node:
                pattern = re.compile(r'"large":"(.*?)"')
                match = pattern.search(image_node)[1]
                image = clean_text(match)
                return image
            else:
                return []

        def get_variations():

            variations_node = response.xpath('//*[@id="twister"]')

            if variations_node:
                s = re.search('"variationValues" : ({.*})', response.text).groups()[0]
                json_acceptable = s.replace("\'", "")
                variations_json = json.loads(json_acceptable)
                sizes = variations_json.get('size_name', [])
                colors = variations_json.get('color_name', [])
                pattern_name = variations_json.get('pattern_name', [])
                style_name = variations_json.get('pattern_name', [])
                return {
                    "sizes": sizes,
                    "colors": colors,
                    "patter_name": pattern_name,
                    "style_name": style_name
                }

        if 'asin' not in self.product:
            self.product['asin'] = get_asin()

        self.product['title'] = get_title()
        self.product['price'] = get_price()
        self.product['category'] = "Home & Kitchen"
        self.product['bsr'] = get_bsr()
        self.product['soldByAmazon'] = get_sold_by_amazon()
        self.product['rating'] = get_rating()
        self.product['isFba'] = get_fba()
        self.product['aboutBullets'] = get_about_bullets()
        self.product['description'] = get_description()
        self.product['hasBuyBox'] = get_buy_box()
        self.product['soldBy'] = get_sold_by()
        self.product['sellers'] = get_sellers()
        self.product['totalReviews'] = get_total_reviews()
        self.product['uuid'] = str(uuid.uuid4())
        self.product['image'] = get_image()
        self.product['variations'] = get_variations()


        # after harvesting all of the product details make second request for the rest of the data
        # only execute 2nd call if the extra categories are missing

        # TODO: convert this to a function
        if 'asin' in self.product:

            buying_options_btn = response.css("#buybox-see-all-buying-choices-announce").get()
            more_sellers_link = response.css("#olp-upd-new").get()
            availability = response.css("#availability").get()
            asin = self.product['asin']

            if buying_options_btn or more_sellers_link or availability:
                url = f"https://www.amazon.com/gp/aod/ajax/ref=dp_olp_NEW_mbc?asin={asin}"
                buying_options_url = get_url(url)
                yield scrapy.Request(url=buying_options_url, callback=self.parse_buying_options)

