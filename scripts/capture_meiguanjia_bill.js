(billNumber) => {
  const allowedHost = "vip3.meiguanjia.net";
  if (location.hostname !== allowedHost || !location.pathname.endsWith("/shair/bill!bill.action")) {
    throw new Error("Open the authenticated Meiguanjia 项目消费 page before capture.");
  }

  const table = [...document.querySelectorAll("table.table-striped")].find((candidate) =>
    [...candidate.rows[0]?.cells ?? []].some((cell) => cell.textContent.includes("单号"))
  );
  if (!table) throw new Error("The rendered bill table was not found.");

  const clean = (value) => (value ?? "").replace(/\s+/g, " ").trim();
  const rows = [...table.rows].filter((row) => /^X\w+$/.test(clean(row.cells[1]?.querySelector("a")?.textContent)));
  const startDate = document.querySelector('input[placeholder="开始日期"]')?.value;
  const endDate = document.querySelector('input[placeholder="结束日期"]')?.value;
  const summaryText = clean(document.querySelector(".summary_number")?.textContent);
  const footerText = clean(
    [...document.querySelectorAll("span")].map((el) => el.textContent).find((text) => /^\s*共\s*\d+\s*条\s*$/.test(text ?? ""))
  );
  const summaryCount = Number(summaryText.match(/本次共查询\s*(\d+)\s*张水单/)?.[1]);
  const footerCount = Number(footerText.match(/共\s*(\d+)\s*条/)?.[1]);

  if (Boolean(startDate) !== Boolean(endDate) || !Number.isFinite(summaryCount) || !Number.isFinite(footerCount)) {
    throw new Error("Date range or completed-result summary is inconsistent; do not capture stale rows.");
  }
  if (summaryCount !== footerCount || rows.length > summaryCount) {
    throw new Error("The result summary and rendered page disagree.");
  }

  const visibleRecords = rows.map((row) => ({
    bill_number: clean(row.cells[1]?.querySelector("a")?.textContent),
    recorded_at: clean(row.cells[2]?.textContent),
  }));
  const outOfRange = startDate && endDate ? visibleRecords.find((record) => {
    const date = record.recorded_at.slice(0, 10);
    return date < startDate || date > endDate;
  }) : null;
  if (outOfRange) throw new Error("A visible row falls outside the selected date range.");

  const row = rows.find((candidate) => clean(candidate.cells[1]?.querySelector("a")?.textContent) === billNumber);
  if (!row) throw new Error(`Bill ${billNumber} is not visible on the current page.`);

  const readQueryValue = (value, key) => {
    if (!value) return null;
    const query = value.includes("?") ? value.slice(value.indexOf("?") + 1) : value;
    return new URLSearchParams(query).get(key);
  };
  const billLink = row.cells[1].querySelector("a");
  const customerSourceId = row.cells[3]?.textContent.match(/\bF\d+\b/)?.[0] ?? null;
  const lineItems = [...(row.cells[7]?.querySelector(":scope > table")?.rows ?? [])]
    .filter((line) => line.cells.length >= 3 && line.cells[0]?.querySelector('a[data-type="item"]'))
    .map((line) => {
      const serviceLink = line.cells[0].querySelector('a[data-type="item"]');
      const serviceParams = serviceLink.getAttribute("data-params") ?? serviceLink.getAttribute("data-hdata");
      const staffTable = line.cells[2]?.querySelector("table");
      const staffAssignments = [...(staffTable?.rows ?? [])]
        .map((staffRow) => {
          const employeeLink = staffRow.cells[0]?.querySelector('a[data-type="emp"]');
          if (!employeeLink) return null;
          const employeeParams = employeeLink.getAttribute("data-hdata") ?? employeeLink.getAttribute("data-params");
          const sourceEmployeeId = readQueryValue(employeeParams, "employeeId");
          if (!sourceEmployeeId) return null;
          const displayLabel = clean(employeeLink.textContent);
          const roleLabel = displayLabel.match(/^\d+号\s*([^[]+)/)?.[1]?.trim() ?? null;
          return {
            source_employee_id: sourceEmployeeId,
            source_assignment_id: readQueryValue(employeeLink.getAttribute("data-params"), "subId"),
            display_label: displayLabel,
            role_label: roleLabel,
            designation_label: clean(staffRow.cells[1]?.querySelector("a")?.textContent),
          };
        })
        .filter(Boolean);

      return {
        source_service_id: readQueryValue(serviceLink.getAttribute("data-hdata"), "itemNo") ?? readQueryValue(serviceParams, "itemNo"),
        source_line_id: readQueryValue(serviceLink.getAttribute("data-params"), "subId"),
        service_label: clean(serviceLink.textContent),
        amount_displayed: clean(line.cells[1]?.textContent),
        staff_assignments: staffAssignments,
      };
    });

  const record = {
    source_record_id: billNumber,
    source_primary_key: billLink.getAttribute("data-pk"),
    source_recorded_at: clean(row.cells[2]?.textContent),
    customer_source_id: customerSourceId,
    posted_amount_displayed: clean(row.cells[6]?.textContent),
    line_items: lineItems,
    source_updated_at: null,
    redacted_fields: ["customer_display_name", "customer_phone", "payment_breakdown", "cashier_display_name"],
  };

  if (!record.source_primary_key || !record.customer_source_id || lineItems.length === 0) {
    throw new Error("Required visible row relationships or source identifiers are missing.");
  }
  if (lineItems.some((item) => !item.source_service_id || item.staff_assignments.some((staff) => !staff.source_employee_id))) {
    throw new Error("A service or employee source identifier could not be read from the rendered row.");
  }

  return {
    source_system: "meiguanjia",
    source_domain: "transaction_consumption",
    source_url: location.href.split("#")[0],
    capture_method: "authenticated_page_dom",
    captured_at: new Date().toISOString(),
    query: { start_date: startDate || null, end_date: endDate || null },
    page: {
      visible_record_count: rows.length,
      source_total_count: summaryCount,
      complete: rows.length === summaryCount,
      selected_record_only: true,
      selected_bill_number: billNumber,
    },
    records: [record],
  };
}
