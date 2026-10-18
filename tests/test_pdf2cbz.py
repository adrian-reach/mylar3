import io
import zipfile

import pytest
from PIL import Image

from mylar import pdf2cbz

pymupdf = pytest.importorskip('pymupdf')


@pytest.mark.parametrize("filename,result", [
    ('Gargoyles 002 (2026).pdf', 'Gargoyles 002 (2026).cbz'),
    ('Gargoyles 002 (2026).pdf.pdf', 'Gargoyles 002 (2026).cbz'),
    ('Gargoyles 002 (2026).PDF', 'Gargoyles 002 (2026).cbz'),
])
@pytest.mark.unit
def test_cbz_name(filename, result):
    assert pdf2cbz.cbz_name(filename) == result


def _image_bytes(colour, fmt='JPEG'):
    buf = io.BytesIO()
    Image.new('RGB', (200, 300), colour).save(buf, fmt)
    return buf.getvalue()


@pytest.mark.unit
def test_convert(tmp_path):
    jpg = _image_bytes('red')
    doc = pymupdf.open()
    #full page image - should be pulled out untouched
    page = doc.new_page(width=200, height=300)
    page.insert_image(page.rect, stream=jpg)
    #text only - has to be rendered
    page = doc.new_page(width=200, height=300)
    page.insert_text((20, 50), 'The End')
    pdf = tmp_path / 'Series 001 (2026).pdf.pdf'
    doc.save(str(pdf))

    cbz = pdf2cbz.convert(str(pdf))

    assert cbz == str(tmp_path / 'Series 001 (2026).cbz')
    assert pdf.exists()
    with zipfile.ZipFile(cbz) as z:
        assert z.namelist() == ['001.jpeg', '002.jpg']
        assert z.read('001.jpeg') == jpg
        assert Image.open(io.BytesIO(z.read('002.jpg'))).format == 'JPEG'


@pytest.mark.unit
def test_convert_existing_cbz(tmp_path):
    doc = pymupdf.open()
    doc.new_page()
    pdf = tmp_path / 'Series 001.pdf'
    doc.save(str(pdf))
    (tmp_path / 'Series 001.cbz').write_bytes(b'existing')

    with pytest.raises(RuntimeError):
        pdf2cbz.convert(str(pdf))
    assert (tmp_path / 'Series 001.cbz').read_bytes() == b'existing'
