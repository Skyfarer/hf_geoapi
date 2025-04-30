This is an geolocation data API for HairForecast. If the HairForecast user doesn't want automatic geolocation, then they can enter a country, and then a city to locate where they wish to get a HairForecast.
The data comes from https://github.com/dr5hn/countries-states-cities-database, which provides geo data in several formats. In this case, I've made use of their sqlite3 format, specifically world.sqlte3 which has tables for cities, countries,
and so on.
This API is built with Python Flask, and exposes a simple API to get query countries, and then cities constrained to a country. Ultimately this gets to a latitude and longitude to use to find a HairForecast.
