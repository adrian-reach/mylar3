#  This file is part of Mylar.
#
#  Mylar is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Mylar is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Mylar.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import zipfile

from mylar import logger

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

#dpi used when a page has to be rendered rather than having its embedded image pulled out as-is
RENDER_DPI = 200


def available():
    return pymupdf is not None


def cbz_name(filename):
    #releases are sometimes named Series 001.pdf.pdf - strip every trailing .pdf, not just the last one
    return re.sub(r'(\.pdf)+$', '', filename, flags=re.IGNORECASE) + '.cbz'


def _page_image(doc, page):
    #most comic pdfs are just one full-page image per page, so grab that image untouched (no quality loss).
    #anything else (vector art, text, multiple images, transparency) gets rendered instead.
    images = page.get_images(full=True)
    if len(images) == 1 and images[0][1] == 0 and not page.get_text().strip():
        xref = images[0][0]
        rects = page.get_image_rects(xref)
        if len(rects) == 1 and abs(rects[0] & page.rect) >= abs(page.rect) * 0.95:
            img = doc.extract_image(xref)
            if img and img.get('image'):
                return img['image'], img['ext']

    pix = page.get_pixmap(dpi=RENDER_DPI)
    return pix.tobytes(output='jpg', jpg_quality=90), 'jpg'


def convert(pdf_path, out_dir=None):
    #converts the pdf into a cbz alongside it (or in out_dir) and returns the path to the new cbz.
    #raises an exception if the conversion couldn't be done - the original pdf is left untouched either way.
    if pymupdf is None:
        raise RuntimeError('PyMuPDF is not installed - run `pip install pymupdf` to enable PDF to CBZ conversion')

    if out_dir is None:
        out_dir = os.path.dirname(pdf_path)
    cbz_path = os.path.join(out_dir, cbz_name(os.path.basename(pdf_path)))
    if os.path.exists(cbz_path):
        raise RuntimeError('%s already exists' % cbz_path)

    with pymupdf.open(pdf_path) as doc:
        if doc.needs_pass:
            raise RuntimeError('pdf is password protected')
        if doc.page_count == 0:
            raise RuntimeError('pdf has no pages')

        pad = max(3, len(str(doc.page_count)))
        try:
            #images are already compressed, so there's nothing to gain by deflating them again
            with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_STORED) as cbz:
                for page in doc:
                    data, ext = _page_image(doc, page)
                    cbz.writestr('%s.%s' % (str(page.number + 1).zfill(pad), ext), data)
        except Exception:
            if os.path.exists(cbz_path):
                os.remove(cbz_path)
            raise

        logger.fdebug('[PDF-TO-CBZ] Converted %s pages from %s to %s' % (doc.page_count, pdf_path, cbz_path))

    return cbz_path
