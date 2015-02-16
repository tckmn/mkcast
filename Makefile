PREFIX = /usr/local

install:
	install -Dm 755 mkcast $(DESTDIR)$(PREFIX)/bin/mkcast
	install -Dm 755 newcast $(DESTDIR)$(PREFIX)/bin/newcast

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/mkcast
	rm -f $(DESTDIR)$(PREFIX)/bin/newcast
